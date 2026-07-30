"""
LLM 工厂模块 — 多 Provider 统一接口

支持 OpenAI / Anthropic / 本地兼容接口的动态切换
完美展示 LangChain 的 ChatModel 抽象层能力
"""
from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from app.core.config import config, LLMProviderConfig
from app.llm.providers import get_provider_vision_meta

PROVIDER_LABELS = {
    "deepseek": "DeepSeek",
    "openai": "OpenAI 兼容",
    "anthropic": "Anthropic Claude",
    "custom": "私有化部署",
}


class LLMFactory:
    """LLM 工厂：根据 provider 名称动态创建 ChatModel 实例"""

    @staticmethod
    def create(provider: str, **overrides) -> BaseChatModel:
        """
        创建 LLM 实例

        Args:
            provider: 提供商名称 (deepseek / openai / anthropic / custom)
            **overrides: 覆盖默认配置的参数 (temperature, max_tokens, model 等)

        Returns:
            BaseChatModel 实例

        示例:
            llm = LLMFactory.create("openai", temperature=0.3)
            llm = LLMFactory.create("custom", model="qwen2.5:14b")
        """
        if provider not in config.providers:
            available = list(config.providers.keys())
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Available providers: {available}"
            )

        cfg = config.providers[provider]
        return LLMFactory._build(cfg, overrides)

    @staticmethod
    def _build(cfg: LLMProviderConfig, overrides: dict) -> BaseChatModel:
        """根据配置构建具体的 ChatModel"""
        model = overrides.get("model") or cfg.model
        temperature = overrides.get("temperature")
        if temperature is None:
            temperature = cfg.temperature
        max_tokens = overrides.get("max_tokens")
        if max_tokens is None:
            max_tokens = cfg.max_tokens

        if not model:
            raise ValueError(
                f"Model not configured for provider '{cfg.provider}'. "
                "Set DEEPSEEK_MODEL (or provider model) in .env or pass model explicitly."
            )

        if cfg.provider == "anthropic":
            return ChatAnthropic(
                model=model,
                api_key=cfg.api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # OpenAI 和 Custom 都使用 ChatOpenAI（兼容 OpenAI API 格式）
        # Custom 可以是 Ollama, vLLM, OneAPI, DeepSeek 等任意兼容接口
        base_url = cfg.base_url
        if base_url and not base_url.endswith("/"):
            base_url += "/"

        return ChatOpenAI(
            model=model,
            api_key=cfg.api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def list_providers() -> list[dict]:
        """列出所有可用 Provider 及其配置（脱敏后）"""
        result = []
        for name, cfg in config.providers.items():
            vision = get_provider_vision_meta(name)
            result.append({
                "name": name,
                "display_name": PROVIDER_LABELS.get(name, name),
                "model": cfg.model,
                "base_url": cfg.base_url,
                "is_default": name == config.agent.default_provider,
                "supports_vision": vision.supports_vision,
                "vision_models": vision.vision_models,
            })
        return result

    @staticmethod
    def update_provider(name: str, **kwargs) -> None:
        """
        动态更新 Provider 配置（用于前端设置页面）
        """
        if name in config.providers:
            cfg = config.providers[name]
            for key, value in kwargs.items():
                if value is not None and hasattr(cfg, key):
                    setattr(cfg, key, value)
        else:
            config.providers[name] = LLMProviderConfig(
                provider=name,
                api_key=kwargs.get("api_key", ""),
                base_url=kwargs.get("base_url"),
                model=kwargs.get("model", "gpt-4o"),
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
            )


# 便捷函数
def get_llm(provider: Optional[str] = None, **overrides) -> BaseChatModel:
    """获取 LLM 实例的便捷函数"""
    provider = provider or config.agent.default_provider
    return LLMFactory.create(provider, **overrides)


def get_available_providers() -> list[str]:
    """获取所有可用 provider 名称"""
    return list(config.providers.keys())
