import pytest
from excelpilot.agent.jev.gates import judge_intent, judge_tier
from excelpilot.agent.jev.policy import evaluate_static_policy, is_destructive_tool, is_write_tool


def test_static_policy_deny_list():
    # Attempting to delete the only sheet
    allowed, reason = evaluate_static_policy("sheet_delete", {"sheet_name": "Sheet1"}, {"sheet_count": 1})
    assert allowed is False
    assert "only remaining worksheet" in reason

    # Attempting to clear excessive cells (> 50,000)
    allowed, reason = evaluate_static_policy("range_clear", {"address": "A1:Z10000"}, {"target_cell_count": 60000})
    assert allowed is False
    assert "exceeds safe threshold" in reason

    # Normal write within policy
    allowed, reason = evaluate_static_policy("range_write_values", {"address": "A1:B10"})
    assert allowed is True
    assert reason is None


def test_tool_classifications():
    assert is_destructive_tool("sheet_delete") is True
    assert is_destructive_tool("range_clear") is True
    assert is_destructive_tool("range_read") is False

    assert is_write_tool("range_write_values") is True
    assert is_write_tool("format_range") is True
    assert is_write_tool("range_read") is False


@pytest.mark.asyncio
async def test_judge_intent_routing():
    intent = await judge_intent("Can you create a pivot table from Sales data?", {})
    assert intent in ["pivot_or_chart", "analyze", "edit_values", "formula", "dashboard"]


@pytest.mark.asyncio
async def test_judge_tier_selection():
    tier = await judge_tier("Summarize total revenue", {"sheet_count": 1, "formula_count": 2})
    assert tier in ["fast", "capable"]
