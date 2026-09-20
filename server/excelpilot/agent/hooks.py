import asyncio
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import SkipToolExecution
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.tools import ToolDefinition

from excelpilot.agent.jev.policy import (
    evaluate_static_policy,
    is_destructive_tool,
    is_wipe_all_request,
    is_write_tool,
    needs_human_approval,
)
from excelpilot.store.db import store
from excelpilot.tools.registry import SKILL_TOOL_SUBSETS


def _tool_args(args: Any) -> dict[str, Any]:
    return args if isinstance(args, dict) else {}


def prepare_tools_for_skill(
    ctx: RunContext[Any], tool_defs: list[ToolDefinition]
) -> list[ToolDefinition]:
    intent = getattr(ctx.deps, "intent", None) if ctx.deps is not None else None
    allowed = SKILL_TOOL_SUBSETS.get(intent or "", None)
    if allowed is None:
        return tool_defs
    if not allowed:
        return []
    filtered = [td for td in tool_defs if td.name in allowed]
    # Never leave the model without a way to write values — "add 25 rows" must not
    # get stuck on an analyze-only subset if routing misfires.
    names = {td.name for td in filtered}
    request = (getattr(ctx.deps, "user_request", "") or "").lower() if ctx.deps is not None else ""
    wipe_all = is_wipe_all_request(request)
    wants_delete = wipe_all or any(w in request for w in ("delete sheet", "remove sheet", "delete the sheet"))
    if wipe_all:
        filtered = [td for td in filtered if td.name != "range_clear"]
        names = {td.name for td in filtered}
        for extra_name in ("workbook_reset", "sheet_list"):
            if extra_name not in names:
                filtered.extend(td for td in tool_defs if td.name == extra_name)
                names.add(extra_name)
    elif wants_delete:
        for extra_name in ("sheet_list", "sheet_delete"):
            if extra_name not in names:
                filtered.extend(td for td in tool_defs if td.name == extra_name)
                names.add(extra_name)
    if "range_write_values" not in names and intent not in {"question_only"} and not wipe_all:
        extra = [td for td in tool_defs if td.name == "range_write_values"]
        filtered.extend(extra)
    return filtered


async def before_tool_execute(
    ctx: RunContext[Any],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Pre-execution gate. Only checks static policy for writes.
    Jev API is ONLY called for truly destructive operations (sheet_delete, etc.)
    to keep latency near-zero for normal operations."""
    tool_name = tool_def.name
    tool_args = _tool_args(args)
    deps = ctx.deps
    session_id = getattr(deps, "session_id", "default") if deps is not None else "default"
    user_request = getattr(deps, "user_request", "") if deps is not None else ""

    # Never let range_clear stand in for "delete all worksheets".
    if tool_name == "range_clear" and is_wipe_all_request(user_request):
        raise SkipToolExecution(
            "Do not clear cells. The user asked to delete worksheets. Call workbook_reset instead."
        )

    # Read-only tools pass through instantly
    if not is_write_tool(tool_name):
        return args

    # Fast static policy check (no API call, ~0ms)
    allowed, block_reason = evaluate_static_policy(tool_name, tool_args)
    if not allowed:
        raise SkipToolExecution(f"Refused by policy: {block_reason}")

    # Skip Excel snapshots on the hot path — they add a full round-trip per write.
    snapshot_id = None

    # Destructive ops always pause for Apply. Bulk writes only pause when the user
    # opted into always-ask — otherwise they silently hang the second prompt.
    from excelpilot.config import settings as _settings

    target_sheet = str(tool_args.get("sheet") or "")
    created = getattr(deps, "created_sheets", set()) if deps is not None else set()
    fresh_sheet = bool(target_sheet) and target_sheet in created and not is_destructive_tool(tool_name)
    always_ask = bool(getattr(_settings, "excelpilot_always_ask_before_writes", False))
    ask = needs_human_approval(tool_name, tool_args) and not fresh_sheet
    if ask and not is_destructive_tool(tool_name) and not always_ask:
        ask = False
    if ask:
        waiter = getattr(deps, "approval_gate", None) if deps is not None else None
        queue = getattr(deps, "event_queue", None) if deps is not None else None
        if waiter is not None and queue is not None:
            n = 0
            try:
                from excelpilot.agent.jev.policy import estimate_write_cells

                n = estimate_write_cells(tool_name, tool_args)
            except Exception:
                n = 0
            await queue.put(
                {
                    "type": "approval_required",
                    "tool": tool_name,
                    "args": {k: tool_args[k] for k in list(tool_args)[:8]},
                    "cells": n,
                    "probs": {"requested": 1.0, "scoped": 0.7, "reversible": 0.8},
                }
            )
            if deps is not None and hasattr(deps, "awaiting_approval"):
                deps.awaiting_approval = True
            try:
                decision = await asyncio.wait_for(waiter.wait(), timeout=120)
            except asyncio.TimeoutError:
                raise SkipToolExecution("Timed out waiting for your approval.")
            finally:
                if deps is not None and hasattr(deps, "awaiting_approval"):
                    deps.awaiting_approval = False
            if not decision:
                raise SkipToolExecution("You declined this change.")
            waiter.clear()
        # If the pane isn't wired, fall through and execute (CLI / tests).

    # Only destructive tools get the Jev gate — everything else is auto-approved
    if is_destructive_tool(tool_name):
        # Lazy import to avoid circular dependency at module level
        from excelpilot.agent.jev.gates import judge_tool_call
        user_request = getattr(deps, "user_request", "") if deps is not None else ""
        verdict, probs = await judge_tool_call(tool_name, tool_args, user_request)
        if verdict == "block":
            store.record_audit(session_id, tool_name, tool_args, "block", "jev", probs, snapshot_id)
            raise SkipToolExecution(
                f"Blocked: {tool_name} was not approved by safety gate (p={probs})."
            )
        asyncio.get_running_loop().run_in_executor(
            None, store.record_audit, session_id, tool_name, tool_args, verdict, "jev", probs, snapshot_id
        )
    else:
        # Auto-approve non-destructive writes — audit off the event loop, no API call
        asyncio.get_running_loop().run_in_executor(
            None, store.record_audit, session_id, tool_name, tool_args, "approve", "local", {}, snapshot_id
        )

    if hasattr(deps, "last_snapshot_id"):
        deps.last_snapshot_id = snapshot_id
    return args


async def after_tool_execute(
    ctx: RunContext[Any],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: dict[str, Any],
    result: Any,
) -> Any:
    """Post-execution hook. Records facts for context, highlights modified ranges."""
    deps = ctx.deps
    tool_args = _tool_args(args)
    if hasattr(deps, "facts_table") and deps is not None:
        key = f"{tool_def.name}:{tool_args.get('address') or tool_args.get('sheet') or 'result'}"
        preview = result
        if isinstance(result, dict):
            preview = {k: result[k] for k in list(result)[:8]}
        deps.facts_table[key] = preview
        deps.tools_used.append(tool_def.name)
    if tool_def.name == "sheet_add" and deps is not None and hasattr(deps, "created_sheets"):
        name = None
        if isinstance(result, dict):
            name = result.get("name")
        name = name or tool_args.get("name")
        if name:
            deps.created_sheets.add(str(name))
    if is_write_tool(tool_def.name):
        from excelpilot.agent.context import invalidate_schema_cache

        invalidate_schema_cache(tool_args.get("sheet") or getattr(deps, "active_sheet", None))
    return result
