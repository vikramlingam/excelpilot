import asyncio
import json
import os
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import Hooks
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    TextPartDelta,
    ThinkingPartDelta,
)
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
from pydantic_ai.usage import UsageLimits

from excelpilot.agent.context import build_sheet_schema_card, compact_schema_for_prompt, load_skill_prompt
from excelpilot.agent.hooks import after_tool_execute, before_tool_execute, prepare_tools_for_skill
from excelpilot.agent.jev.policy import (
    extract_sheet_delete_target,
    heuristic_intent,
    heuristic_tier,
    is_wipe_all_request,
)
from excelpilot.config import settings
from excelpilot.store.db import store
from excelpilot.telemetry import logger
from excelpilot.tools.registry import SKILL_TOOL_SUBSETS, TOOL_FUNCTIONS


@dataclass
class TurnDeps:
    user_request: str
    session_id: str
    active_sheet: str
    intent: str
    schema_card: dict[str, Any] = field(default_factory=dict)
    facts_table: dict[str, Any] = field(default_factory=dict)
    tools_used: list[str] = field(default_factory=list)
    created_sheets: set[str] = field(default_factory=set)
    awaiting_approval: bool = False
    last_snapshot_id: str | None = None
    event_queue: asyncio.Queue | None = None
    approval_gate: Any = None
    last_stream_at: float = 0.0


def _serialize_result(result: Any) -> str:
    try:
        text = json.dumps(result, default=str)
    except Exception:
        text = str(result)
    return text[:500]


class Orchestrator:
    def __init__(self) -> None:
        if settings.openrouter_api_key:
            os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key
        for name, fn in TOOL_FUNCTIONS.items():
            fn.__name__ = name
        self._histories: dict[str, list[Any]] = {}
        self._approval_gates: dict[str, "_ApprovalGate"] = {}
        self._hooks = Hooks(
            prepare_tools=prepare_tools_for_skill,
            before_tool_execute=before_tool_execute,
            after_tool_execute=after_tool_execute,
        )
        self._agents: dict[str, Agent[TurnDeps, str]] = {}

    def _get_agent(self, tier_or_model: str = "fast") -> Agent[TurnDeps, str]:
        if tier_or_model in self._agents:
            return self._agents[tier_or_model]
        if tier_or_model == "capable":
            model_name = settings.openrouter_model_capable
        elif tier_or_model in ("fast", "auto", ""):
            model_name = settings.openrouter_model
        else:
            model_name = tier_or_model

        fallbacks = [m for m in settings.fallback_models if m != model_name]
        extra: dict[str, Any] = {"models": fallbacks} if fallbacks else {}
        agent: Agent[TurnDeps, str] = Agent(
            model=OpenRouterModel(model_name),
            deps_type=TurnDeps,
            tools=list(TOOL_FUNCTIONS.values()),
            capabilities=[self._hooks],
            model_settings=OpenRouterModelSettings(
                temperature=0.1,
                parallel_tool_calls=False,
                timeout=max(120.0, float(settings.llm_timeout_s)),
                openrouter_reasoning={"enabled": False},
                extra_body=extra or None,
                extra_headers={
                    "HTTP-Referer": settings.openrouter_app_url,
                    "X-Title": settings.openrouter_app_title,
                },
            ),
            instructions=self._instructions,
            retries=1,
        )
        self._agents[tier_or_model] = agent
        return agent

    @staticmethod
    async def _instructions(ctx: RunContext[TurnDeps]) -> str:
        deps = ctx.deps
        prompt = load_skill_prompt(deps.intent)
        allowed = set(SKILL_TOOL_SUBSETS.get(deps.intent, set()))
        if is_wipe_all_request(deps.user_request):
            allowed |= {"workbook_reset", "sheet_delete", "sheet_list"}
            allowed.discard("range_clear")
        schema = compact_schema_for_prompt(deps.schema_card) if deps.schema_card else "(not read)"
        extra = ""
        if is_wipe_all_request(deps.user_request):
            extra = (
                "The user asked to delete worksheets. Call workbook_reset ONCE. "
                "Do NOT call range_clear. Excel keeps one blank Sheet1. "
                "Do not claim the tool is missing.\n"
            )
        return (
            f"{prompt}\n\n"
            f"Active sheet: '{deps.active_sheet}'. Use exactly this sheet name in tool calls unless the user "
            f"names another sheet.\n{schema}\n{extra}"
            "Rules: use the column letters and row range above to build addresses; "
            "call tools sequentially (sheet_add before writing into that sheet); "
            "do not call range_read when the schema answers the question; "
            "if a tool reports the sheet/table already exists, reuse it and continue; "
            "after tools finish, reply in 1-2 sentences stating exactly what changed and where.\n"
            f"Allowed tools: {', '.join(sorted(allowed)) or '(none — answer directly)'}"
        )

    def resolve_approval(self, session_id: str, approved: bool) -> None:
        gate = self._approval_gates.get(session_id)
        if gate is not None:
            gate.resolve(approved)

    async def _destructive_turn(
        self,
        *,
        tool_name: str,
        tool_args: dict[str, Any],
        user_message: str,
        session_id: str,
        intent: str,
        start: float,
        run_tool: Any,
        recap_ok: Any,
        card_cells: int = 0,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """One Jev call → Apply/Decline card → execute. No chat model involved."""
        from excelpilot.agent.jev.gates import judge_tool_call

        def done(text: str, used: list[str]) -> dict[str, Any]:
            return {
                "type": "done",
                "full_text": text,
                "cost_usd": 0,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "intent": intent,
                "tools_used": used,
            }

        gate = _ApprovalGate()
        self._approval_gates[session_id] = gate
        try:
            yield {"type": "status", "message": "Checking with Jev…"}
            try:
                verdict, probs = await asyncio.wait_for(
                    judge_tool_call(tool_name, tool_args, user_message), timeout=5.0
                )
            except Exception:
                verdict, probs = "review", {"requested": 0.5, "scoped": 0.5, "reversible": 0.5}

            if verdict == "block":
                yield done(f"Jev blocked `{tool_name}` for this request. Nothing was changed.", [])
                return

            if verdict == "approve" and settings.excelpilot_always_ask_before_writes is False and tool_name != "workbook_reset":
                # Jev is confident and the user did not opt into always-ask: skip the card.
                pass
            else:
                yield {
                    "type": "approval_required",
                    "tool": tool_name,
                    "args": tool_args,
                    "cells": card_cells,
                    "probs": probs,
                }
                try:
                    approved = await asyncio.wait_for(gate.wait(), timeout=120)
                except asyncio.TimeoutError:
                    approved = False
                if not approved:
                    yield done("Declined. Nothing was changed.", [])
                    return

            yield {"type": "status", "message": f"Running {tool_name}…"}
            yield {"type": "tool_call", "id": tool_name, "tool": tool_name, "args": tool_args}
            try:
                result = await run_tool()
                yield {
                    "type": "tool_result",
                    "id": tool_name,
                    "tool": tool_name,
                    "result": _serialize_result(result),
                }
                recap = recap_ok(result)
            except Exception as err:
                recap = f"Could not run {tool_name}: {err}"
            yield done(recap, [tool_name])
        finally:
            self._approval_gates.pop(session_id, None)

    async def execute_turn(
        self,
        user_message: str,
        session_id: str,
        active_sheet: str = "Sheet1",
        selection: str | None = None,
        selected_model: str | None = None,
        file_base64: str | None = None,
        file_name: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        start = time.perf_counter()
        pdf_block = ""
        extracted_pdf = None
        if file_base64:
            yield {"type": "status", "message": "Reading PDF…"}
            try:
                from excelpilot.analysis.pdf_parser import (
                    default_ingest_instruction,
                    extract_from_base64,
                    maybe_vision_extract,
                    decode_pdf_base64,
                )

                extracted_pdf = extract_from_base64(file_base64, file_name or "document.pdf")
                if not extracted_pdf.tables and len((extracted_pdf.text or "").strip()) < 40:
                    try:
                        data = decode_pdf_base64(file_base64)
                    except Exception:
                        data = b""
                    if data:
                        extracted_pdf = await maybe_vision_extract(extracted_pdf, data)
                pdf_block = extracted_pdf.prompt_block()
                if not (user_message or "").strip():
                    user_message = default_ingest_instruction(file_name or "document.pdf")
            except Exception as err:
                logger.warning("PDF extract failed", error=str(err))
                pdf_block = (
                    f'[Attached PDF Document: "{file_name or "document.pdf"}"]\n'
                    f"Could not extract tables ({err}). Ask the user to paste the data if needed."
                )
                if not (user_message or "").strip():
                    from excelpilot.analysis.pdf_parser import default_ingest_instruction

                    user_message = default_ingest_instruction(file_name or "document.pdf")

        intent = heuristic_intent(user_message)
        if pdf_block:
            intent = "edit_values"
        tier = heuristic_tier(user_message, {})

        if selected_model and selected_model.strip() and selected_model != "auto":
            active_model = selected_model.strip()
            model_tier_label = active_model.split("/")[-1]
            agent_key = active_model
        else:
            active_model = settings.openrouter_model_capable if tier == "capable" else settings.openrouter_model
            model_tier_label = tier
            agent_key = tier

        yield {"type": "intent", "intent": intent}
        yield {"type": "tier", "tier": model_tier_label, "model": active_model}

        if extracted_pdf is not None and extracted_pdf.excel_grids():
            from excelpilot.analysis.pdf_parser import ingest_extracted
            from excelpilot.bridge.router import router as excel_router

            if not excel_router.officejs_bridge.is_connected:
                yield {
                    "type": "done",
                    "full_text": (
                        "Excel add-in is not connected, so I cannot write the extracted tables. "
                        "Reopen the task pane, wait for Connected, then send the PDF again."
                    ),
                    "cost_usd": 0,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "intent": intent,
                    "tools_used": [],
                }
                return

            yield {"type": "status", "message": "Writing PDF tables to Excel…"}
            try:
                written = await ingest_extracted(extracted_pdf)
                recap = (
                    f"Extracted {written['rows']} rows from '{extracted_pdf.file_name}' "
                    f"into sheet '{written['sheet']}' ({written['address']})"
                    + (f" as table {', '.join(written['tables'])}." if written.get("tables") else ".")
                )
                yield {
                    "type": "done",
                    "full_text": recap,
                    "cost_usd": 0,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "intent": intent,
                    "tools_used": ["sheet_add", "range_write_values", "table_create", "autofit"],
                }
                return
            except Exception as err:
                logger.warning("PDF ingest write failed; falling back to agent", error=str(err))
                pdf_block += f"\nWrite attempt failed ({err}). Use tools to insert the extracted tables."

        if is_wipe_all_request(user_message):
            from excelpilot.tools.sheets import workbook_reset

            def _recap_reset(result: Any) -> str:
                kept = result.get("kept", "Sheet1") if isinstance(result, dict) else "Sheet1"
                deleted = result.get("deleted", []) if isinstance(result, dict) else []
                return (
                    f"Reset the workbook. Deleted {len(deleted)} sheet(s)"
                    + (f" ({', '.join(deleted)})" if deleted else "")
                    + f". Left blank '{kept}' — Excel requires at least one worksheet."
                )

            async for ev in self._destructive_turn(
                tool_name="workbook_reset",
                tool_args={"keep_name": "Sheet1"},
                user_message=user_message,
                session_id=session_id,
                intent=intent,
                start=start,
                run_tool=lambda: workbook_reset("Sheet1"),
                recap_ok=_recap_reset,
            ):
                yield ev
            return

        known_sheets: list[str] = []
        try:
            from excelpilot.bridge.router import router

            infos = await asyncio.wait_for(router.list_sheets(), timeout=2.0)
            known_sheets = [s.name for s in infos]
        except Exception:
            known_sheets = []
        target = extract_sheet_delete_target(user_message, known_sheets)
        if target:
            from excelpilot.tools.sheets import sheet_delete

            sheet_name = active_sheet if target == "__ACTIVE__" else target
            match = next((s for s in known_sheets if s.lower() == sheet_name.lower()), None)

            def _done(text: str) -> dict[str, Any]:
                return {
                    "type": "done",
                    "full_text": text,
                    "cost_usd": 0,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "intent": intent,
                    "tools_used": [],
                }

            if known_sheets and match is None:
                yield _done(f"There is no worksheet named '{sheet_name}'. Sheets: {', '.join(known_sheets)}.")
                return
            sheet_name = match or sheet_name
            if len(known_sheets) <= 1:
                yield _done(
                    f"'{sheet_name}' is the only worksheet. Excel requires at least one, so it cannot be "
                    "deleted. Ask me to reset the workbook to clear it instead."
                )
                return

            async for ev in self._destructive_turn(
                tool_name="sheet_delete",
                tool_args={"sheet_name": sheet_name},
                user_message=user_message,
                session_id=session_id,
                intent=intent,
                start=start,
                run_tool=lambda: sheet_delete(sheet_name),
                recap_ok=lambda _r: f"Deleted worksheet '{sheet_name}'.",
            ):
                yield ev
            return

        # Schema is cached for 45s; a miss costs ~2 quick Office.js reads. The model needs real
        # column letters + row counts to build correct addresses — skipping this caused wrong edits.
        schema_card: dict[str, Any] = {}
        if intent != "question_only":
            yield {"type": "status", "message": "Reading sheet…"}
            try:
                schema_card = await asyncio.wait_for(build_sheet_schema_card(active_sheet), timeout=4.0)
            except Exception as err:
                logger.warning("Schema read skipped", error=str(err))
        yield {"type": "status", "message": "Calling model…"}

        prompt = user_message if not selection else f"{user_message}\nSelection: {selection}"
        if pdf_block:
            prompt = f"{prompt}\n\n{pdf_block}\n\nUse sheet_add, range_write_values, table_create, then autofit. Write the extracted grid as a 2-D array in one range_write_values call starting at A1 of the new sheet."
        deps = TurnDeps(
            user_request=user_message,
            session_id=session_id,
            active_sheet=active_sheet,
            intent=intent,
            schema_card=schema_card,
        )
        history = self._histories.get(session_id)
        if history and len(history) > 12:
            history = history[-12:]

        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        gate = _ApprovalGate()
        self._approval_gates[session_id] = gate
        deps.event_queue = queue
        deps.approval_gate = gate

        async def on_events(_ctx: RunContext[TurnDeps], stream: Any) -> None:
            # Called once per model/tool node. Do NOT send a terminal sentinel here —
            # that used to abort the waiter before follow-up model calls / Apply cards.
            try:
                async for event in stream:
                    deps.last_stream_at = time.perf_counter()
                    mapped = self._map(event)
                    if mapped:
                        await queue.put(mapped)
            except (asyncio.CancelledError, GeneratorExit):
                raise
            except Exception as err:
                logger.warning("event stream handler error", error=str(err))

        yield {"type": "status", "message": "Calling model…"}
        full_text = ""
        try:
            run_task = asyncio.create_task(
                self._get_agent(agent_key).run(
                    prompt,
                    deps=deps,
                    message_history=history,
                    event_stream_handler=on_events,
                    usage_limits=UsageLimits(request_limit=24, tool_calls_limit=24),
                )
            )
            idle_limit = max(180.0, float(settings.llm_timeout_s) + 90.0)
            last_activity = time.perf_counter()
            deps.last_stream_at = last_activity
            while True:
                now = time.perf_counter()
                last_activity = max(last_activity, float(getattr(deps, "last_stream_at", 0.0) or 0.0))
                if getattr(deps, "awaiting_approval", False):
                    last_activity = now
                idle = now - last_activity
                if idle >= idle_limit:
                    run_task.cancel()
                    try:
                        await run_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    raise TimeoutError("Model call timed out")
                getter = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait(
                    {getter, run_task},
                    timeout=min(5.0, max(0.1, idle_limit - idle)),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if not done:
                    getter.cancel()
                    yield {"type": "status", "message": "Working…"}
                    continue
                if getter in done:
                    item = getter.result()
                    last_activity = time.perf_counter()
                    if item is not None:
                        yield item
                    continue
                getter.cancel()
                try:
                    await getter
                except (asyncio.CancelledError, Exception):
                    pass
                while not queue.empty():
                    item = queue.get_nowait()
                    if item is not None:
                        yield item
                break
            result = await run_task
            full_text = str(result.output or "").strip()
            self._histories[session_id] = result.all_messages()[-12:]
        except TimeoutError:
            logger.error("Agent execution timed out")
            yield {"type": "error", "message": "The model took too long. Please try again."}
            full_text = "The model took too long and the request was stopped. Please try again."
        except Exception as err:
            logger.error("Agent execution error", error=str(err))
            yield {"type": "error", "message": str(err)}
            full_text = f"An error occurred: {err!s}"
        finally:
            self._approval_gates.pop(session_id, None)

        if not str(full_text or "").strip():
            if deps.tools_used:
                full_text = "Done. Applied " + ", ".join(deps.tools_used) + "."
            else:
                full_text = "I didn't change the sheet."

        latency = round((time.perf_counter() - start) * 1000, 2)
        store.record_cost(session_id, 0.0004)
        yield {
            "type": "done",
            "full_text": full_text,
            "cost_usd": 0.0004,
            "latency_ms": latency,
            "intent": intent,
            "tools_used": deps.tools_used,
        }

    @staticmethod
    def _map(event: Any) -> dict[str, Any] | None:
        if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
            if event.delta.content_delta:
                return {"type": "text_delta", "delta": event.delta.content_delta}
            return None
        if isinstance(event, PartDeltaEvent) and isinstance(event.delta, ThinkingPartDelta):
            return {"type": "status", "message": "Thinking…"}
        if isinstance(event, FunctionToolCallEvent):
            part = event.part
            args = part.args if isinstance(part.args, dict) else {}
            return {
                "type": "tool_call",
                "id": part.tool_call_id,
                "tool": part.tool_name,
                "args": args,
                "status": "running",
            }
        if isinstance(event, FunctionToolResultEvent):
            part = event.part
            return {
                "type": "tool_result",
                "id": getattr(part, "tool_call_id", ""),
                "tool": getattr(part, "tool_name", ""),
                "result": _serialize_result(getattr(part, "content", None)),
                "status": "done",
            }
        return None


class _ApprovalGate:
    """One in-flight human decision per session. Recreated after each resolve."""

    def __init__(self) -> None:
        self._future: asyncio.Future[bool] | None = None

    def _ensure(self) -> asyncio.Future[bool]:
        loop = asyncio.get_running_loop()
        if self._future is None or self._future.done():
            self._future = loop.create_future()
        return self._future

    async def wait(self) -> bool:
        return await self._ensure()

    def resolve(self, approved: bool) -> None:
        fut = self._future
        if fut is not None and not fut.done():
            fut.set_result(bool(approved))

    def clear(self) -> None:
        self._future = None


orchestrator = Orchestrator()


