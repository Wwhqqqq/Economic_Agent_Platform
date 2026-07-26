"""
Settings persistence — merge runtime overrides into data/settings.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import config, LLMProviderConfig

SETTINGS_FILE = Path(__file__).resolve().parents[3] / "data" / "settings.json"


def _ensure_dir() -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_persisted_settings() -> dict[str, Any]:
    """Load persisted settings from disk."""
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[SettingsStore] Failed to load {SETTINGS_FILE}: {exc}")
        return {}


def apply_persisted_settings() -> None:
    """Merge persisted provider overrides into in-memory config on startup."""
    data = load_persisted_settings()
    providers = data.get("providers") or {}
    for name, fields in providers.items():
        if name in config.providers:
            cfg = config.providers[name]
            for key, value in fields.items():
                if hasattr(cfg, key) and value is not None:
                    setattr(cfg, key, value)
        else:
            config.providers[name] = LLMProviderConfig(
                provider=name,
                api_key=fields.get("api_key", ""),
                base_url=fields.get("base_url"),
                model=fields.get("model", "gpt-4o"),
                temperature=float(fields.get("temperature", 0.7)),
                max_tokens=int(fields.get("max_tokens", 4096)),
            )

    default_provider = data.get("default_provider")
    if default_provider and default_provider in config.providers:
        config.agent.default_provider = default_provider  # type: ignore[assignment]


def save_provider(name: str, fields: dict[str, Any]) -> None:
    """Persist a single provider's mutable fields."""
    _ensure_dir()
    data = load_persisted_settings()
    providers = data.setdefault("providers", {})
    current = providers.get(name, {})
    for key, value in fields.items():
        if value is not None:
            current[key] = value
    providers[name] = current
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_default_provider(name: str) -> None:
    _ensure_dir()
    data = load_persisted_settings()
    data["default_provider"] = name
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    config.agent.default_provider = name  # type: ignore[assignment]
