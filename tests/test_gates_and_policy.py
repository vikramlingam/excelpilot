import pytest
from excelpilot.agent.jev.gates import judge_intent, judge_tier
from excelpilot.agent.jev.policy import (
    estimate_write_cells,
    evaluate_static_policy,
    extract_sheet_delete_target,
    heuristic_intent,
    is_destructive_tool,
    is_wipe_all_request,
    is_write_tool,
    needs_human_approval,
)


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


def test_wipe_all_detection():
    assert is_wipe_all_request("delete all worksheets") is True
    assert is_wipe_all_request("reset the workbook") is True
    assert is_wipe_all_request("clear column B") is False
    assert is_wipe_all_request("delete sheet Sales") is False


def test_sheet_delete_target_extraction():
    sheets = ["Sheet1", "Inventory", "Q1 Data"]
    assert extract_sheet_delete_target("delete the Inventory worksheet", sheets) == "Inventory"
    assert extract_sheet_delete_target("remove sheet Inventory", sheets) == "Inventory"
    assert extract_sheet_delete_target("please delete 'Q1 Data' tab", sheets) == "Q1 Data"
    assert extract_sheet_delete_target("delete Inventory", sheets) == "Inventory"
    assert extract_sheet_delete_target("delete this sheet", sheets) == "__ACTIVE__"
    assert extract_sheet_delete_target("delete all worksheets", sheets) is None
    assert extract_sheet_delete_target("delete column B", sheets) is None
    assert extract_sheet_delete_target("make B bold", sheets) is None


def test_additional_rows_is_edit_not_analyze():
    assert heuristic_intent("write additional 25 rows of data") == "edit_values"
    assert heuristic_intent("add 25 more rows") == "edit_values"
    assert heuristic_intent("analyze this workbook") == "analyze"
    assert heuristic_intent("write additional 25 rows of data") == "edit_values"
    assert heuristic_intent("add 25 more rows") == "edit_values"
    assert heuristic_intent("analyze this workbook") == "analyze"


def test_bulk_write_needs_approval_flag_but_default_is_not_always_ask():
    from excelpilot.config import settings

    small = {"address": "A1", "values": [["x"]]}
    assert needs_human_approval("range_write_values", small) is False
    bulk = {"address": "A108:D132", "values": [[1, 2, 3, 4] for _ in range(25)]}
    assert estimate_write_cells("range_write_values", bulk) == 100
    assert needs_human_approval("range_write_values", bulk) is True
    assert needs_human_approval("sheet_delete", {"sheet": "Sheet1"}) is True
    assert needs_human_approval("workbook_reset", {}) is True
    assert settings.excelpilot_always_ask_before_writes is False



@pytest.mark.asyncio
async def test_judge_intent_routing():
    intent = await judge_intent("Can you create a pivot table from Sales data?", {})
    assert intent in ["pivot_or_chart", "analyze", "edit_values", "formula", "dashboard"]


@pytest.mark.asyncio
async def test_judge_tier_selection():
    tier = await judge_tier("Summarize total revenue", {"sheet_count": 1, "formula_count": 2})
    assert tier in ["fast", "capable"]
