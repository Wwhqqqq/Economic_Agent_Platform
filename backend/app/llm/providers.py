from __future__ import annotations

from dataclasses import dataclass

VISION_CAPABLE = {
    "openai": {
        "supports_vision": True,
        "vision_models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "max_images_per_message": 4,
    },
    "anthropic": {
        "supports_vision": True,
        "vision_models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "max_images_per_message": 4,
    },
    "custom": {
        "supports_vision": False,
        "vision_models": [],
        "max_images_per_message": 0,
    },
    "deepseek": {
        "supports_vision": False,
        "vision_models": [],
        "max_images_per_message": 0,
    },
}


@dataclass
class ProviderVisionMeta:
    provider: str
    supports_vision: bool
    vision_models: list[str]
    max_images_per_message: int


def get_provider_vision_meta(provider: str) -> ProviderVisionMeta:
    meta = VISION_CAPABLE.get(provider, VISION_CAPABLE["deepseek"])
    return ProviderVisionMeta(
        provider=provider,
        supports_vision=bool(meta.get("supports_vision")),
        vision_models=list(meta.get("vision_models") or []),
        max_images_per_message=int(meta.get("max_images_per_message") or 0),
    )


def provider_supports_vision(provider: str, model: str | None = None) -> bool:
    meta = get_provider_vision_meta(provider)
    if not meta.supports_vision:
        return False
    if model:
        return any(model.startswith(m.split("-")[0]) or model in meta.vision_models for m in meta.vision_models)
    return True


def pick_vision_provider(preferred: str | None = None) -> str | None:
    from app.core.config import config

    def _has_api_key(name: str) -> bool:
        cfg = config.providers.get(name)
        return bool(cfg and (cfg.api_key or "").strip())

    order: list[str] = []
    if preferred and provider_supports_vision(preferred) and _has_api_key(preferred):
        order.append(preferred)
    for name in ("openai", "anthropic", "custom"):
        if (
            name not in order
            and name in config.providers
            and provider_supports_vision(name)
            and _has_api_key(name)
        ):
            order.append(name)
    return order[0] if order else None
