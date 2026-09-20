import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from excelpilot.agent.jev.policy import heuristic_intent
from excelpilot.agent.orchestrator import Orchestrator, TurnDeps
from excelpilot.bridge.models import BridgeError


def test_sales_ledger_prompt_routes_to_pivot_skill():
    msg = (
        "On the active sheet, generate a sales ledger table of 15 realistic orders "
        "with columns OrderID, Region, Product, Units Sold, Unit Price, and Total Revenue. "
        "Convert this range into an official Excel Table named SalesOrders. Then create a "
        "new sheet called Region_Summary and build a Pivot Table summarizing Total Revenue "
        "by Region and Product."
    )
    assert heuristic_intent(msg) == "pivot_or_chart"


@pytest.mark.asyncio
async def test_sheet_add_reuses_existing_name():
    from excelpilot.tools import sheets

    with patch("excelpilot.tools.sheets.router.add_sheet", new=AsyncMock()) as add:
        add.side_effect = BridgeError("ItemAlreadyExists", "A resource with the same name or identifier already exists.")
        result = await sheets.sheet_add("Income_Statement")
    assert result["name"] == "Income_Statement"
    assert result["existed"] is True


@pytest.mark.asyncio
async def test_table_create_reuses_existing_name():
    from excelpilot.tools import tables

    with patch("excelpilot.tools.tables.router.create_table", new=AsyncMock()) as create:
        create.side_effect = BridgeError("ItemAlreadyExists", "A resource with the same name or identifier already exists.")
        result = await tables.table_create("Sheet1", "A1:F16", table_name="SalesOrders")
    assert result == "SalesOrders"


@pytest.mark.asyncio
async def test_execute_turn_survives_multiple_event_streams():
    """Regression: ending the first model-node stream used to abort the waiter,
    then kill the still-running agent after idle_limit (the 'took too long' bug)."""
    orch = Orchestrator()

    class EmptyStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class Result:
        output = "created the sales ledger and pivot"
        def all_messages(self):
            return []

    async def fake_run(*_a, **kwargs):
        handler = kwargs["event_stream_handler"]
        await handler(SimpleNamespace(), EmptyStream())
        await asyncio.sleep(0.05)
        await handler(SimpleNamespace(), EmptyStream())
        await asyncio.sleep(0.05)
        return Result()

    fake_agent = SimpleNamespace(run=fake_run)

    with (
        patch.object(orch, "_get_agent", return_value=fake_agent),
        patch("excelpilot.agent.orchestrator.build_sheet_schema_card", new=AsyncMock(return_value={})),
        patch("excelpilot.bridge.router.router.list_sheets", new=AsyncMock(return_value=[])),
        patch("excelpilot.agent.orchestrator.store.record_cost"),
    ):
        events = []
        async for ev in orch.execute_turn("add a total row", session_id="t1", active_sheet="Sheet1"):
            events.append(ev)

    types = [e.get("type") for e in events]
    assert "error" not in types
    assert "done" in types
    done = next(e for e in events if e["type"] == "done")
    assert "sales ledger" in done["full_text"]
