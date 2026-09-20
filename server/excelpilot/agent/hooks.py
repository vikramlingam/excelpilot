from typing import Any

from excelpilot.agent.jev.gates import judge_tool_call
from excelpilot.agent.jev.policy import evaluate_static_policy, is_write_tool
from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router
from excelpilot.telemetry import logger


async def before_tool_execute(
    tool_name: str,
    args: dict[str, Any],
    user_request: str,
    session_id: str,
) -> tuple[bool, str, str | None, dict[str, float]]:
    # Returns (allowed, verdict, snapshot_id, probs)
    if not is_write_tool(tool_name):
        return True, "approve", None, {}

    # Check deterministic static deny-list
    allowed, block_reason = evaluate_static_policy(tool_name, args)
    if not allowed:
        return False, "block", None, {}

    # Snapshot target range before write if sheet and address are specified
    snapshot_id = None
    target_sheet = args.get("sheet") or args.get("sheet_name")
    target_addr = args.get("address") or args.get("range")
    if target_sheet and target_addr:
        try:
            ref = RangeRef(sheet=target_sheet, address=target_addr)
            snapshot_id = await router.snapshot(ref)
        except Exception as err:
            logger.warning("Pre-write snapshot failed", error=str(err))

    # Evaluate J3 gate
    verdict, probs = await judge_tool_call(
        tool_name=tool_name,
        tool_args=args,
        user_request=user_request,
    )

    if verdict == "block":
        return False, "block", snapshot_id, probs

    return True, verdict, snapshot_id, probs
