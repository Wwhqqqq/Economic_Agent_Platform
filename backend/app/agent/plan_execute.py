"""
Plan-Execute Agent — 先规划后执行

流程: Plan → Execute Steps (ReAct) → Evaluate → (可选 Replan) → Aggregate Final
"""
import json
import re
from typing import AsyncIterator

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda

from app.agent.base import (
    BaseAgent,
    AgentConfig,
    AgentEvent,
    AgentEventType,
    AgentResponse,
)
from app.agent.react_agent import ReActAgent
from app.agent.runtime import (
    create_llm,
    load_agent_context,
    message_content,
    normalize_agent_config,
    resolve_system_prompt,
    run_react_loop,
)
from app.memory.manager import memory_manager

MAX_REPLAN_ATTEMPTS = 1


class PlanExecuteAgent(BaseAgent):
    """Plan-Execute Agent — 复杂多步骤任务编排"""

    name = "plan_execute_agent"
    description = "Plan-Execute agent for complex multi-step tasks"

    def __init__(self):
        self._react_agent = ReActAgent()

    async def _generate_plan(
        self,
        task: str,
        context: str,
        previous_feedback: str | None = None,
    ) -> tuple[list[dict], str]:
        """用 DeepSeek 生成执行计划。"""
        llm = create_llm(AgentConfig(), temperature=0.3)
        feedback_block = ""
        if previous_feedback:
            feedback_block = f"\nPrevious attempt feedback:\n{previous_feedback}\n"

        prompt = f"""You are a task planning expert. Break down the following task into concrete,
executable steps. Each step should be specific and actionable.

Context:
{context}
{feedback_block}
Task:
{task}

Respond in JSON format:
{{
  "overview": "Brief overview of the plan",
  "steps": [
    {{"step": 1, "description": "...", "expected_output": "...", "tools_needed": []}}
  ]
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = message_content(response)

        try:
            plan = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                plan = json.loads(match.group())
            else:
                plan = {
                    "overview": "Single-step execution",
                    "steps": [
                        {
                            "step": 1,
                            "description": task,
                            "expected_output": "task result",
                        }
                    ],
                }

        return plan.get("steps", []), plan.get("overview", "")

    async def _evaluate_execution(
        self,
        task: str,
        overview: str,
        step_results: list[dict],
    ) -> dict:
        """评估步骤执行是否满足任务目标，决定是否需要重规划。"""
        llm = create_llm(AgentConfig(), temperature=0.2)
        steps_text = "\n\n".join(
            f"Step {item['step']} ({item['description']}):\n{item['result']}"
            for item in step_results
        )
        prompt = f"""You are a task evaluator. Review whether the executed plan satisfies the user task.

Task:
{task}

Plan overview:
{overview}

Executed results:
{steps_text}

Respond in JSON only:
{{
  "complete": true,
  "needs_replan": false,
  "gaps": ["..."],
  "feedback": "..."
}}"""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = message_content(response)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {
            "complete": True,
            "needs_replan": False,
            "gaps": [],
            "feedback": "",
        }

    async def _execute_steps(
        self,
        steps: list[dict],
        config: AgentConfig,
    ) -> list[dict]:
        """逐步调用 ReAct Agent 执行计划。"""
        step_results: list[dict] = []
        for step in steps:
            step_prompt = (
                f"Execute the following step from a larger plan:\n\n"
                f"Step {step['step']}: {step['description']}\n"
                f"Expected output: {step.get('expected_output', 'N/A')}\n\n"
                f"Use tools when needed and provide a focused result for this step only."
            )
            step_result = await self._react_agent.invoke(
                step_prompt, config, persist_memory=False
            )
            step_results.append(
                {
                    "step": step["step"],
                    "description": step["description"],
                    "result": step_result.output,
                    "tool_calls": step_result.tool_calls,
                }
            )
        return step_results

    async def _aggregate_final(
        self,
        task: str,
        overview: str,
        step_results: list[dict],
        config: AgentConfig,
    ) -> AgentResponse:
        """汇总所有步骤结果生成最终答案。"""
        summary_prompt = (
            f"Original task:\n{task}\n\n"
            f"Plan overview:\n{overview}\n\n"
            "Summarize the following step-by-step execution results into a "
            "cohesive final answer:\n\n"
            + "\n\n".join(
                f"Step {item['step']}: {item['result']}" for item in step_results
            )
        )
        return await self._react_agent.invoke(
            summary_prompt, config, persist_memory=False
        )

    async def invoke(
        self, user_input: str, config: AgentConfig = None
    ) -> AgentResponse:
        config = normalize_agent_config(config)
        events: list[AgentEvent] = []
        context, _citations = await load_agent_context(
            config,
            user_input,
            resolve_system_prompt(config),
        )

        step_results: list[dict] = []
        overview = ""
        feedback = None

        for attempt in range(MAX_REPLAN_ATTEMPTS + 1):
            steps, overview = await self._generate_plan(
                user_input,
                context,
                previous_feedback=feedback,
            )
            events.append(
                AgentEvent(
                    type=AgentEventType.INTERMEDIATE,
                    data={
                        "phase": "plan",
                        "attempt": attempt + 1,
                        "overview": overview,
                        "steps": steps,
                    },
                )
            )

            step_results = await self._execute_steps(steps, config)
            for item in step_results:
                events.append(
                    AgentEvent(
                        type=AgentEventType.INTERMEDIATE,
                        data={
                            "phase": "execute",
                            "step": item["step"],
                            "description": item["description"],
                            "result": item["result"][:300],
                        },
                    )
                )

            evaluation = await self._evaluate_execution(
                user_input,
                overview,
                step_results,
            )
            events.append(
                AgentEvent(
                    type=AgentEventType.INTERMEDIATE,
                    data={"phase": "evaluate", **evaluation},
                )
            )

            if not evaluation.get("needs_replan") or attempt >= MAX_REPLAN_ATTEMPTS:
                break
            feedback = evaluation.get("feedback") or ", ".join(
                evaluation.get("gaps", [])
            )

        summary_result = await self._aggregate_final(
            user_input,
            overview,
            step_results,
            config,
        )

        all_tool_calls = [
            tool_call
            for item in step_results
            for tool_call in item.get("tool_calls", [])
        ]
        all_tool_calls.extend(summary_result.tool_calls)

        await memory_manager.save_context(
            config.session_id,
            user_input,
            summary_result.output,
        )

        return AgentResponse(
            output=summary_result.output,
            events=events,
            tool_calls=all_tool_calls,
            execution_time_ms=summary_result.execution_time_ms,
        )

    async def stream(
        self, user_input: str, config: AgentConfig = None
    ) -> AsyncIterator[AgentEvent]:
        """流式执行：逐步推送 plan / execute / evaluate / final 事件。"""
        config = normalize_agent_config(config)
        context, _citations = await load_agent_context(
            config,
            user_input,
            resolve_system_prompt(config),
        )

        step_results: list[dict] = []
        overview = ""
        feedback = None
        final_output = ""
        all_tool_calls: list[dict] = []

        try:
            if citations:
                yield AgentEvent(type=AgentEventType.CITATION, data={"citations": citations})
            yield AgentEvent(
                type=AgentEventType.THINKING,
                data={"phase": "planning", "message": "正在分析任务并生成执行计划..."},
            )

            for attempt in range(MAX_REPLAN_ATTEMPTS + 1):
                steps, overview = await self._generate_plan(
                    user_input,
                    context,
                    previous_feedback=feedback,
                )
                yield AgentEvent(
                    type=AgentEventType.INTERMEDIATE,
                    data={
                        "phase": "plan",
                        "attempt": attempt + 1,
                        "overview": overview,
                        "steps": steps,
                    },
                )

                step_results = []
                for step in steps:
                    yield AgentEvent(
                        type=AgentEventType.STEP,
                        data={
                            "step": step.get("step", 0),
                            "title": f"执行步骤 {step.get('step', '')}",
                            "content": step.get("description", ""),
                            "status": "running",
                        },
                    )
                    yield AgentEvent(
                        type=AgentEventType.INTERMEDIATE,
                        data={
                            "phase": "execute_start",
                            "step": step["step"],
                            "description": step["description"],
                        },
                    )

                    step_prompt = (
                        f"Execute the following step from a larger plan:\n\n"
                        f"Step {step['step']}: {step['description']}\n"
                        f"Expected output: {step.get('expected_output', 'N/A')}\n\n"
                        f"Use tools when needed and provide a focused result for this step only."
                    )

                    step_output = ""
                    step_tool_calls: list[dict] = []
                    async for event in run_react_loop(
                        step_prompt,
                        config,
                        persist_memory=False,
                        emit_done=False,
                        thinking_message=f"正在执行步骤 {step['step']}...",
                    ):
                        if event.type in {
                            AgentEventType.TOOL_CALL,
                            AgentEventType.TOOL_RESULT,
                            AgentEventType.REASONING,
                            AgentEventType.THINKING,
                        }:
                            event.metadata["plan_step"] = step["step"]
                            yield event
                        elif event.type == AgentEventType.FINAL:
                            step_output = event.data.get("output", "")
                            step_tool_calls = event.data.get("tool_calls", [])

                    step_results.append(
                        {
                            "step": step["step"],
                            "description": step["description"],
                            "result": step_output,
                            "tool_calls": step_tool_calls,
                        }
                    )
                    all_tool_calls.extend(step_tool_calls)

                    yield AgentEvent(
                        type=AgentEventType.INTERMEDIATE,
                        data={
                            "phase": "execute_done",
                            "step": step["step"],
                            "result": step_output[:300],
                        },
                    )

                evaluation = await self._evaluate_execution(
                    user_input,
                    overview,
                    step_results,
                )
                yield AgentEvent(
                    type=AgentEventType.INTERMEDIATE,
                    data={"phase": "evaluate", **evaluation},
                )

                if not evaluation.get("needs_replan") or attempt >= MAX_REPLAN_ATTEMPTS:
                    break

                feedback = evaluation.get("feedback") or ", ".join(
                    evaluation.get("gaps", [])
                )
                yield AgentEvent(
                    type=AgentEventType.THINKING,
                    data={
                        "phase": "replan",
                        "message": "评估未通过，正在重新规划...",
                        "feedback": feedback,
                    },
                )

            yield AgentEvent(
                type=AgentEventType.THINKING,
                data={"phase": "aggregate", "message": "正在汇总各步骤结果..."},
            )

            summary_prompt = (
                f"Original task:\n{user_input}\n\n"
                f"Plan overview:\n{overview}\n\n"
                "Summarize the following step-by-step execution results into a "
                "cohesive final answer:\n\n"
                + "\n\n".join(
                    f"Step {item['step']}: {item['result']}" for item in step_results
                )
            )
            async for event in run_react_loop(
                summary_prompt,
                config,
                persist_memory=False,
                emit_done=False,
                thinking_message="正在生成最终汇总...",
            ):
                if event.type in {
                    AgentEventType.TOOL_CALL,
                    AgentEventType.TOOL_RESULT,
                    AgentEventType.REASONING,
                    AgentEventType.THINKING,
                }:
                    event.metadata["phase"] = "aggregate"
                    yield event
                elif event.type == AgentEventType.FINAL:
                    final_output = event.data.get("output", final_output)
                    all_tool_calls.extend(event.data.get("tool_calls", []))

            yield AgentEvent(
                type=AgentEventType.FINAL,
                data={"output": final_output, "tool_calls": all_tool_calls},
            )

            await memory_manager.save_context(
                config.session_id,
                user_input,
                final_output,
            )
            yield AgentEvent(type=AgentEventType.DONE)

        except Exception as exc:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={"message": str(exc)},
            )
            yield AgentEvent(type=AgentEventType.DONE)

    async def to_runnable(self):
        async def _run(inputs: dict):
            user_input = inputs.get("input", "")
            session_id = inputs.get("session_id", "default")
            config = normalize_agent_config(AgentConfig(session_id=session_id))
            response = await self.invoke(user_input, config)
            return {"output": response.output}

        return RunnableLambda(_run)
