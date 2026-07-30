from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

SKILL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@dataclass
class SkillManifest:
    name: str
    version: str = "1.0.0"
    display_name: str = ""
    description: str = ""
    category: str = "general"
    category_label: str = ""
    icon: str = "🔧"
    slash_command: str = ""
    user_invocable: bool = True
    expert_equippable: bool = True
    runtime_type: str = "hybrid"
    engine_preference: str = "any"
    pipeline_name: str = ""
    fallback: str = "react"
    required_tools: list[str] = field(default_factory=list)
    system_prompt_path: str = "prompts/system.md"
    context_policy_path: str = "policies/context.yaml"
    context_strategy: dict = field(default_factory=dict)
    pack_root: str = ""
    body: str = ""

    @property
    def slash(self) -> str:
        return self.slash_command or f"/{self.name}"


def _split_front_matter(text: str) -> tuple[dict, str]:
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return meta, body


def _read_optional_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _read_optional_text(path: Path) -> str:
    if not path.is_file():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_skill_manifest(skill_md_path: str | Path) -> SkillManifest:
    path = Path(skill_md_path)
    pack_root = path.parent
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)

    name = str(meta.get("name") or pack_root.name)
    if not SKILL_NAME_PATTERN.match(name):
        raise ValueError(f"Invalid skill name: {name}")

    display = meta.get("display") or {}
    invocation = meta.get("invocation") or {}
    runtime = meta.get("runtime") or {}
    requires = meta.get("requires") or {}
    prompts = meta.get("prompts") or {}
    context = meta.get("context") or {}

    system_rel = prompts.get("system", "prompts/system.md")
    context_rel = context.get("file", "policies/context.yaml")
    context_data = _read_optional_yaml(pack_root / context_rel)

    return SkillManifest(
        name=name,
        version=str(meta.get("version", "1.0.0")),
        display_name=str(display.get("name") or name),
        description=str(display.get("description") or body[:200]),
        category=str(display.get("category") or "general"),
        category_label=str(display.get("category_label") or display.get("category") or "通用"),
        icon=str(display.get("icon") or "🔧"),
        slash_command=str(invocation.get("slash_command") or f"/{name}"),
        user_invocable=bool(invocation.get("user_invocable", True)),
        expert_equippable=bool(invocation.get("expert_equippable", True)),
        runtime_type=str(runtime.get("type") or "hybrid"),
        engine_preference=str(runtime.get("engine_preference") or "any"),
        pipeline_name=str(runtime.get("pipeline") or ""),
        fallback=str(runtime.get("fallback") or "react"),
        required_tools=list(requires.get("tools") or []),
        system_prompt_path=str(system_rel),
        context_policy_path=str(context_rel),
        context_strategy={
            "max_history": int(context_data.get("max_history", 20)),
            "include_knowledge": bool(context_data.get("include_knowledge", True)),
            "include_entities": bool(context_data.get("include_entities", True)),
            "include_long_term": bool(context_data.get("include_long_term", True)),
            "rerank": bool(context_data.get("rerank", True)),
            "content_types": context_data.get("content_types"),
            "knowledge_top_k": int(context_data.get("knowledge_top_k", 8)),
        },
        pack_root=str(pack_root),
        body=body,
    )


def load_system_prompt(manifest: SkillManifest) -> str:
    path = Path(manifest.pack_root) / manifest.system_prompt_path
    return _read_optional_text(path)


def discover_skillpacks(skills_root: str | Path) -> list[SkillManifest]:
    root = Path(skills_root)
    if not root.is_dir():
        return []
    manifests: list[SkillManifest] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        skill_md = entry / "SKILL.md"
        if skill_md.is_file():
            try:
                manifests.append(load_skill_manifest(skill_md))
            except Exception as exc:
                print(f"[SkillLoader] Skip {entry.name}: {exc}")
    return manifests
