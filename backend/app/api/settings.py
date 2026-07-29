"""系统设置 API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.llm.factory import LLMFactory
from app.models.settings import LLMProviderUpdate
from app.core.settings_store import save_provider, save_default_provider
from app.schemas.user_context import UserContext
from app.services.auth import AUTH_ENABLED, get_current_user
from app.services.audit_log import log_action

router = APIRouter(prefix="/api/settings", tags=["settings"])


class DefaultProviderRequest(BaseModel):
    provider: str


@router.get("/llm")
async def get_llm_config():
    from app.core.config import config
    providers = []
    for p in LLMFactory.list_providers():
        name = p["name"]
        cfg = config.providers.get(name)
        providers.append({
            **p,
            "temperature": cfg.temperature if cfg else 0.7,
            "max_tokens": cfg.max_tokens if cfg else 4096,
            "has_api_key": bool(cfg and cfg.api_key and cfg.api_key not in ("", "not-needed", "sk-your-key-here", "sk-your-deepseek-key")),
        })
    return {
        "providers": providers,
        "default_provider": config.agent.default_provider,
    }


async def require_llm_editor(user: UserContext = Depends(get_current_user)) -> UserContext:
    if AUTH_ENABLED and not user.is_member:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="升级会员后可配置个人模型接入")
    return user


@router.put("/llm")
async def update_llm_config(req: LLMProviderUpdate, user: UserContext = Depends(require_llm_editor)):
    LLMFactory.update_provider(
        name=req.provider,
        api_key=req.api_key,
        base_url=req.base_url,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    save_provider(req.provider, {
        "api_key": req.api_key,
        "base_url": req.base_url,
        "model": req.model,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    })
    log_action("settings.llm.update", user.username, {"provider": req.provider})
    return {"status": "updated", "provider": req.provider}


@router.put("/llm/default")
async def set_default_provider(req: DefaultProviderRequest, user: UserContext = Depends(require_llm_editor)):
    save_default_provider(req.provider)
    log_action("settings.llm.default", user.username, {"provider": req.provider})
    return {"status": "updated", "default_provider": req.provider}
