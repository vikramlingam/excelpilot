import time
from types import SimpleNamespace

import pytest

from excelpilot.agent.jev.client import JevClient
from excelpilot.agent.jev.policy import heuristic_intent, heuristic_tier
from typesafe_sdk import Noul, TypeSafeAuthenticationError


@pytest.mark.asyncio
async def test_jev_client_probe_snapshot():
    client = JevClient()
    snap = client.status_snapshot()
    assert snap["backend"] in ["typesafe", "openrouter", "offline", "unprobed"]
    assert snap["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_typesafe_auth_failure_is_circuit_broken(monkeypatch):
    client = JevClient()
    calls = {"typesafe": 0, "openrouter": 0}

    async def fail_typesafe(*args, **kwargs):
        calls["typesafe"] += 1
        raise TypeSafeAuthenticationError("bad key")

    async def ok_openrouter(*args, **kwargs):
        calls["openrouter"] += 1
        return SimpleNamespace(
            model="typesafe/jev-1.13", answers={"probe": SimpleNamespace(noul=0.9)}
        )

    if client._typesafe_client is None:
        client._typesafe_client = SimpleNamespace(system_one=fail_typesafe)
    else:
        monkeypatch.setattr(client._typesafe_client, "system_one", fail_typesafe)

    client._openrouter_client = SimpleNamespace(system_one=ok_openrouter)

    questions = {"probe": Noul(instructions="Is this a test?")}
    first = await client.ask({"type": "t"}, questions)
    second = await client.ask({"type": "t"}, questions)  # identical → served from verdict cache
    third = await client.ask({"type": "t2"}, questions)  # new state → TypeSafe skipped, OpenRouter hit

    assert first is not None
    assert second is not None
    assert third is not None
    assert calls["typesafe"] == 1  # circuit broken after the first 401
    assert calls["openrouter"] == 2  # first + third; second was a cache hit
    assert client.cache_hits == 1
    assert client.active_backend == "openrouter"
    assert client._skip_typesafe_until > time.monotonic()


def test_intent_heuristics():
    assert heuristic_intent("Analyze this workbook") == "analyze"
    assert heuristic_intent("Create a pivot table") == "pivot_or_chart"
    assert heuristic_intent("What is XLOOKUP?") == "question_only"
    assert heuristic_tier("Build a financial model across sheets", {}) == "capable"
    assert heuristic_tier("Bold the header row", {"sheet_count": 1}) == "fast"
