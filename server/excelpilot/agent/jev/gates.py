from typing import Any

from typesafe_sdk import Choice, Noul, Score

from excelpilot.agent.jev.client import jev_client
from excelpilot.agent.jev.policy import is_destructive_tool
from excelpilot.config import settings


async def judge_intent(
    user_message: str, schema_summary: dict[str, Any] | None = None
) -> str:
    # J1: Intent routing
    state = {
        "user_message": user_message,
        "active_sheet": (schema_summary or {}).get("name", "Sheet1"),
        "has_tables": bool((schema_summary or {}).get("tables")),
    }
    questions = {
        "intent": Choice(
            instructions="Identify the primary user intent for this Excel request.",
            criteria={
                "analyze": "Analyze workbook structure or health",
                "edit_values": "Edit, clean, or enter cell data",
                "formula": "Author or explain formulas",
                "format": "Apply formatting and visual styles",
                "pivot_or_chart": "Create or modify PivotTables and charts",
                "dashboard": "Design dashboards with KPI cards and slicers",
                "script": "Generate and run Office.js TypeScript",
                "question_only": "General question without modifying workbook",
            },
        )
    }
    resp = await jev_client.ask(state, questions)
    if resp and "intent" in resp.answers:
        ans = resp.answers["intent"]
        if hasattr(ans, "choice"):
            return str(ans.choice)
    return "analyze" if "analy" in user_message.lower() else "edit_values"


async def judge_tier(
    user_message: str, workbook_stats: dict[str, Any]
) -> str:
    # J2: Capability tier selection (fast vs capable)
    state = {
        "user_message": user_message,
        "sheet_count": workbook_stats.get("sheet_count", 1),
        "formula_count": workbook_stats.get("formula_count", 0),
        "cross_sheet_refs": workbook_stats.get("cross_sheet_refs", 0),
    }
    questions = {
        "tier": Choice(
            instructions="Decide if this task requires high capability reasoning or if fast execution is sufficient.",
            criteria={
                "fast": "Standard edits, formulas, or formatting tasks",
                "capable": "Complex financial modeling or multi-sheet reconciliation",
            },
        )
    }
    resp = await jev_client.ask(state, questions)
    if resp and "tier" in resp.answers:
        ans = resp.answers["tier"]
        if hasattr(ans, "choice"):
            return str(ans.choice)
    return "fast"


async def judge_tool_call(
    tool_name: str,
    tool_args: dict[str, Any],
    user_request: str,
    policy_notes: str = "",
) -> tuple[str, dict[str, float]]:
    # J3: Tool-call gate for writes. Returns verdict: approve, block, or review
    if is_destructive_tool(tool_name):
        return "review", {"requested": 0.5, "scoped": 0.5, "reversible": 0.5}

    state = {
        "tool_name": tool_name,
        "target_sheet": tool_args.get("sheet") or tool_args.get("sheet_name", ""),
        "target_address": tool_args.get("address") or tool_args.get("range", ""),
        "user_request": user_request,
        "policy_notes": policy_notes,
    }
    questions = {
        "requested": Noul(
            instructions="Does the user's explicit request call for this modification?"
        ),
        "scoped": Noul(
            instructions="Is the targeted sheet and range within the scope requested?"
        ),
        "reversible": Noul(
            instructions="Is this operation safe and reversible with an undo snapshot?"
        ),
    }

    resp = await jev_client.ask(state, questions)
    if not resp:
        return "review", {"requested": 0.0, "scoped": 0.0, "reversible": 0.0}

    req_p = getattr(resp.answers.get("requested"), "noul", 0.5)
    scp_p = getattr(resp.answers.get("scoped"), "noul", 0.5)
    rev_p = getattr(resp.answers.get("reversible"), "noul", 0.5)

    probs = {"requested": req_p, "scoped": scp_p, "reversible": rev_p}

    if any(p <= settings.jev_block_threshold for p in probs.values()):
        return "block", probs

    if all(p >= settings.jev_approve_threshold for p in probs.values()):
        return "approve", probs

    return "review", probs


async def judge_script_safety(
    code: str, api_calls: list[str], user_request: str
) -> tuple[bool, str]:
    # J4: Script gate for Office.js TypeScript
    state = {
        "code_snippet": code[:1000],
        "api_calls": api_calls,
        "user_request": user_request,
    }
    questions = {
        "safe_surface": Noul(
            instructions="Does the script only use standard Excel manipulation APIs without dangerous calls?"
        ),
        "matches_request": Noul(
            instructions="Does the script directly match what the user requested?"
        ),
        "blast_radius": Score(
            instructions="Rate the blast radius of this script.",
            criteria={
                "cell": "Affects single cell only",
                "range": "Affects bounded range",
                "sheet": "Affects entire sheet",
                "workbook": "Affects whole workbook structure",
            },
        ),
    }
    resp = await jev_client.ask(state, questions)
    if not resp:
        return False, "Jev judge offline. Human review required for script execution."

    safe_p = getattr(resp.answers.get("safe_surface"), "noul", 0.0)
    match_p = getattr(resp.answers.get("matches_request"), "noul", 0.0)

    if safe_p >= 0.85 and match_p >= 0.85:
        return True, "Script approved by safety gate."
    return False, f"Script safety review required: safe={safe_p:.2f}, matches={match_p:.2f}"


async def judge_claim_support(
    sentence: str, facts_table: dict[str, Any]
) -> tuple[str, float]:
    # J5: Claim verification against computed facts
    state = {"sentence": sentence, "facts_table": facts_table}
    questions = {
        "support": Choice(
            instructions="Is every factual figure in the sentence supported by the facts table?",
            criteria={
                "supported": "Claim matches numbers in facts table",
                "unsupported": "Claim does not match numbers in facts table",
                "not_a_claim": "Sentence is descriptive and contains no factual figures",
            },
        )
    }
    resp = await jev_client.ask(state, questions)
    if resp and "support" in resp.answers:
        ans = resp.answers["support"]
        choice = getattr(ans, "choice", "supported")
        conf = getattr(ans, "confidence", 0.9)
        return str(choice), float(conf)
    return "supported", 1.0


async def judge_task_done(
    user_request: str, tools_used: list[str], final_summary: str
) -> bool:
    # J8: Task completion verification
    state = {
        "user_request": user_request,
        "tools_used": tools_used,
        "final_summary": final_summary,
    }
    questions = {
        "complete": Noul(
            instructions="Has the agent completely addressed all requirements in the user request?"
        )
    }
    resp = await jev_client.ask(state, questions)
    if resp and "complete" in resp.answers:
        prob = getattr(resp.answers["complete"], "noul", 0.7)
        return bool(prob >= 0.60)
    return True
