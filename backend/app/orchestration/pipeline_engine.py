from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from app.agent.base import AgentConfig
from app.agent.runtime import create_llm, message_content
from app.rag.entity_extractor import extract_json_blob
from app.skills.base import SkillResult
from app.skills.executor import SkillExecutor
from app.tools.registry import tool_registry
from langchain_core.messages import HumanMessage


class PipelineEngine:
    """YAML step executor: builtin / tool / llm."""

    def __init__(self, pack_root: str | Path):
        self.pack_root = Path(pack_root)

    def _load_pipeline(self, pipeline_name: str) -> dict:
        path = self.pack_root / "pipelines" / f"{pipeline_name}.yaml"
        if not path.is_file():
            raise FileNotFoundError(f"Pipeline not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _render(self, template: Any, ctx: dict) -> Any:
        if isinstance(template, str):
            out = template
            for key, val in ctx.items():
                out = out.replace(f"{{{{ {key} }}}}", str(val))
                out = out.replace(f"{{{{{key}}}}}", str(val))
            return out
        if isinstance(template, dict):
            return {k: self._render(v, ctx) for k, v in template.items()}
        return template

    async def _run_step(self, step: dict, ctx: dict, config: AgentConfig) -> Any:
        step_type = step.get("type", "builtin")
        step_id = step.get("id", "step")

        if step_type == "builtin":
            handler = step.get("handler", "")
            if handler == "extract_financial_json":
                raw = ctx.get("_user_input", "")
                data = extract_json_blob(raw)
                if not data:
                    raise ValueError("No financial JSON found in input")
                return data
            raise ValueError(f"Unknown builtin handler: {handler}")

        if step_type == "tool":
            tool_name = step.get("tool", "")
            args = self._render(step.get("input", {}), ctx)
            if isinstance(args, dict) and len(args) == 1:
                first_val = next(iter(args.values()))
                if isinstance(first_val, (dict, list)):
                    args = {"data": json.dumps(first_val, ensure_ascii=False)}
            record = await SkillExecutor.run_tool_step(tool_name, **args)
            if not record.get("success"):
                raise RuntimeError(record.get("result", "tool failed"))
            return record.get("result", "")

        if step_type == "llm":
            llm = create_llm(config, temperature=0.3)
            prompt_path = step.get("prompt_template")
            prompt_text = ""
            if prompt_path:
                p = self.pack_root / prompt_path
                if p.is_file():
                    prompt_text = p.read_text(encoding="utf-8")
            inputs = self._render(step.get("input", {}), ctx)
            prompt = f"{prompt_text}\n\nContext:\n{json.dumps(inputs, ensure_ascii=False, indent=2)}"
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return message_content(response)

        raise ValueError(f"Unknown pipeline step type: {step_type}")

    async def run(
        self,
        pipeline_name: str,
        user_input: str,
        config: AgentConfig | None = None,
    ) -> SkillResult:
        from app.agent.base import AgentConfig as AC

        config = config or AC()
        pipeline = self._load_pipeline(pipeline_name)
        ctx: dict[str, Any] = {"_user_input": user_input}
        tool_calls: list[dict] = []

        try:
            for step in pipeline.get("steps", []):
                output = await self._run_step(step, ctx, config)
                out_key = step.get("output")
                if out_key:
                    ctx[out_key] = output
                if step.get("type") == "tool":
                    tool_calls.append({"tool": step.get("tool"), "result": str(output)[:500]})

            final_key = pipeline.get("output", {}).get("field") if isinstance(pipeline.get("output"), dict) else None
            final = ctx.get(final_key or "final_report") or ctx.get("final_report") or str(ctx.get("ratio_result", ""))
            if not final:
                final = json.dumps({k: v for k, v in ctx.items() if not k.startswith("_")}, ensure_ascii=False)[:4000]

            return SkillResult(success=True, output=str(final), tool_calls=tool_calls)
        except Exception as exc:
            on_error = pipeline.get("on_error", {})
            if on_error.get("fallback") == "react":
                return SkillResult(success=False, output="", tool_calls=tool_calls, error=str(exc))
            return SkillResult(success=False, output="", tool_calls=tool_calls, error=str(exc))

    @staticmethod
    def pipeline_trigger_matches(pack_root: Path, pipeline_name: str, user_input: str) -> bool:
        path = pack_root / "pipelines" / f"{pipeline_name}.yaml"
        if not path.is_file():
            return False
        with open(path, "r", encoding="utf-8") as f:
            pipeline = yaml.safe_load(f) or {}
        trigger = pipeline.get("trigger", {})
        if trigger.get("type") == "json_schema_match":
            return extract_json_blob(user_input) is not None
        return bool(re.search(r"\{[\s\S]*\"balance_sheet\"[\s\S]*\}", user_input))
