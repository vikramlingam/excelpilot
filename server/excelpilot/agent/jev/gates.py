from typing import Any

from typesafe_sdk import Choice, Noul

from excelpilot.agent.jev.client import jev_client
from excelpilot.agent.jev.policy import heuristic_intent, heuristic_tier, is_destructive_tool
from excelpilot.config import settings

VALID_INTENTS = {
    "analyze",
    "edit_values",
    "formula",
    "format",
    "pivot_or_chart",
    "dashboard",
    "script",
    "question_only",
}


def _choice(resp: Any, key: str) -> str | None:
    if not resp or key not in getattr(resp, "answers", {}):
        return None
    ans = resp.answers[key]
    value = getattr(ans, "choice", None)
    return str(value) if value is not None else None


def _noul(resp: Any, key: str, default: float = 0.5) -> float:
    if not resp or key not in getattr(resp, "answers", {}):
        return default
    return float(getattr(resp.answers[key], "noul", default) or default)


async def route_turn(
    user_message: str,
    schema_summary: dict[str, Any] | None = None,
    workbook_stats: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Single Jev call for intent (J1) and capability tier (J2)."""
    schema = schema_summary or {}
    stats = workbook_stats or {}
    state = {
        "user_message": user_message,
        "active_sheet": schema.get("sheet") or schema.get("name", "Sheet1"),
        "has_tables": bool(schema.get("tables")),
        "sheet_count": stats.get("sheet_count", 1),
        "formula_count": stats.get("formula_count", 0),
        "cross_sheet_refs": stats.get("cross_sheet_refs", 0),
        "used_range": schema.get("used_range", ""),
    }
    questions = {
        "intent": Choice(
            instructions="Identify the primary user intent for this Excel request.",
            criteria={
                "analyze": "Analyze, audit, summarize, or explain the workbook",
                "edit_values": "Edit, clean, fill, or enter cell data",
                "formula": "Author, fix, or explain formulas",
                "format": "Apply formatting, number formats, or conditional styles",
                "pivot_or_chart": "Create or modify PivotTables or charts",
                "dashboard": "Design a dashboard with KPI cards and slicers",
                "script": "Generate and run Office.js TypeScript",
                "question_only": "A question that does not require changing the workbook",
            },
        ),
        "tier": Choice(
            instructions="Pick fast for ordinary edits. Pick capable only for multi-sheet financial logic.",
            criteria={
                "fast": "Standard edits, formulas, formatting, or lookups",
                "capable": "Complex financial modeling or multi-sheet reconciliation",
            },
        ),
    }
    resp = await jev_client.ask(state, questions)
    intent = _choice(resp, "intent") or heuristic_intent(user_message)
    if intent not in VALID_INTENTS:
        intent = heuristic_intent(user_message)
    tier = _choice(resp, "tier") or heuristic_tier(user_message, stats)
    if tier not in {"fast", "capable"}:
        tier = "fast"
    return intent, tier


async def judge_intent(user_message: str, schema_summary: dict[str, Any] | None = None) -> str:
    intent, _ = await route_turn(user_message, schema_summary)
    return intent


async def judge_tier(user_message: str, workbook_stats: dict[str, Any]) -> str:
    _, tier = await route_turn(user_message, workbook_stats=workbook_stats)
    return tier


async def judge_tool_call(
    tool_name: str,
    tool_args: dict[str, Any],
    user_request: str,
    policy_notes: str = "",
) -> tuple[str, dict[str, float]]:
    state = {
        "tool_name": tool_name,
        "target_sheet": tool_args.get("sheet") or tool_args.get("sheet_name", ""),
        "target_address": tool_args.get("address") or tool_args.get("range", ""),
        "user_request": user_request,
        "policy_notes": policy_notes or (
            "Destructive. workbook_reset leaves one blank sheet because Excel forbids zero sheets. "
            "Do not treat range_clear as a substitute for deleting worksheets."
        ),
    }
    questions = {
        "requested": Noul(instructions="Does the user's explicit request call for this modification?"),
        "scoped": Noul(instructions="Is the targeted sheet and range within the scope requested?"),
        "reversible": Noul(instructions="Is this operation acceptable if the user confirmed in the UI?"),
    }
    resp = await jev_client.ask(state, questions)
    if not resp:
        return "review", {"requested": 0.0, "scoped": 0.0, "reversible": 0.0}

    probs = {
        "requested": _noul(resp, "requested"),
        "scoped": _noul(resp, "scoped"),
        "reversible": _noul(resp, "reversible"),
    }
    if any(p <= settings.jev_block_threshold for p in probs.values()):
        return "block", probs
    if all(p >= settings.jev_approve_threshold for p in probs.values()):
        return "approve", probs
    return "review", probs


async def judge_script_safety(
    code: str, api_calls: list[str], user_request: str
) -> tuple[bool, str]:
    state = {
        "code_snippet": code[:1000],
        "api_calls": api_calls[:20],
        "user_request": user_request,
    }
    questions = {
        "safe_surface": Noul(
            instructions="Does the script only use standard Excel APIs without network, eval, or file access?"
        ),
        "matches_request": Noul(instructions="Does the script directly match what the user requested?"),
    }
    resp = await jev_client.ask(state, questions)
    if not resp:
        return False, "Jev judge offline. Human review required for script execution."
    safe_p = _noul(resp, "safe_surface", 0.0)
    match_p = _noul(resp, "matches_request", 0.0)
    if safe_p >= 0.85 and match_p >= 0.85:
        return True, "Script approved by safety gate."
    return False, f"Script safety review required: safe={safe_p:.2f}, matches={match_p:.2f}"


async def judge_claim_support(
    sentence: str, facts_table: dict[str, Any]
) -> tuple[str, float]:
    if not facts_table:
        return "not_a_claim", 1.0
    state = {"sentence": sentence, "facts_table": facts_table}
    questions = {
        "support": Choice(
            instructions="Is every factual figure in the sentence supported by the facts table?",
            criteria={
                "supported": "Claim matches numbers in the facts table",
                "unsupported": "Claim does not match numbers in the facts table",
                "not_a_claim": "Sentence is descriptive and contains no factual figures",
            },
        )
    }
    resp = await jev_client.ask(state, questions)
    if resp and "support" in resp.answers:
        ans = resp.answers["support"]
        return str(getattr(ans, "choice", "supported")), float(getattr(ans, "confidence", 0.9) or 0.9)
    return "supported", 1.0


async def judge_task_done(
    user_request: str, tools_used: list[str], final_summary: str
) -> bool:
    state = {
        "user_request": user_request,
        "tools_used": tools_used[:20],
        "final_summary": final_summary[:1500],
    }
    questions = {
        "complete": Noul(
            instructions="Has the agent completely addressed all requirements in the user request?"
        )
    }
    resp = await jev_client.ask(state, questions)
    if resp and "complete" in resp.answers:
        return bool(_noul(resp, "complete", 0.7) >= 0.60)
    return True
