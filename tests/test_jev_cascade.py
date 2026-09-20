import pytest
from excelpilot.agent.jev.client import JevClient
from typesafe_sdk import Noul


@pytest.mark.asyncio
async def test_jev_client_probe():
    client = JevClient()
    probe = await client.probe()
    assert probe["status"] in ["ok", "offline"]
    assert probe["backend"] in ["typesafe", "openrouter", "offline"]
    assert probe["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_jev_client_ask_basic():
    client = JevClient()
    state = {"text": "hello"}
    questions = {"friendly": Noul(instructions="Is this greeting friendly?")}
    res = await client.ask(state, questions)
    if res is not None:
        assert "friendly" in res.answers
        ans = res.answers["friendly"]
        assert hasattr(ans, "noul")
        assert 0.0 <= ans.noul <= 1.0
