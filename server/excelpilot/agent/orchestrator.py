import os
import time
from collections.abc import AsyncGenerator
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel

from excelpilot.agent.context import build_sheet_schema_card, load_skill_prompt
from excelpilot.agent.jev.gates import judge_intent, judge_tier
from excelpilot.agent.verify import verify_claims
from excelpilot.config import settings
from excelpilot.store.db import store
from excelpilot.telemetry import logger
from excelpilot.tools.registry import SKILL_TOOL_SUBSETS, mcp


class Orchestrator:
    """Coordinates intent routing, model tiers, tool execution, and verification."""

    def __init__(self) -> None:
        if settings.openrouter_api_key:
            os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

    def _get_model(self, tier: str) -> OpenRouterModel:
        model_name = (
            settings.openrouter_model_capable
            if tier == "capable"
            else settings.openrouter_model
        )
        return OpenRouterModel(model_name)

    async def execute_turn(
        self,
        user_message: str,
        session_id: str,
        active_sheet: str = "Sheet1",
        selection: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.perf_counter()

        # Step 1: Fetch active sheet schema
        schema_card = await build_sheet_schema_card(active_sheet)

        # Step 2: J1 Intent routing
        intent = await judge_intent(user_message, schema_card)
        yield {"type": "intent", "intent": intent}

        # Step 3: J2 Tier selection
        stats = {"sheet_count": 1, "formula_count": 5, "cross_sheet_refs": 0}
        tier = await judge_tier(user_message, stats)
        model = self._get_model(tier)
        yield {"type": "tier", "tier": tier, "model": model.model_name}

        # Step 4: Load skill prompt and build system instructions
        system_prompt = load_skill_prompt(intent)
        prompt_with_context = (
            f"{system_prompt}\n\nActive Sheet: {active_sheet}\n"
            f"Selection: {selection or 'None'}\n"
            f"Schema Summary: {schema_card}"
        )

        agent = Agent(model=model, system_prompt=prompt_with_context)

        # Step 5: Attach tools filtered to skill subset
        subset = SKILL_TOOL_SUBSETS.get(intent, set())
        for tool_name in subset:
            if hasattr(mcp, "tools") and tool_name in mcp.tools:
                t_obj = mcp.tools[tool_name]
                # Register wrapper on agent
                agent.tool_plain(t_obj.fn)

        facts_table: dict[str, Any] = {}

        try:
            # Stream the agent response
            async with agent.run_stream(user_message) as result:
                async for text in result.stream_text(delta=True):
                    yield {"type": "text_delta", "delta": text}

                full_text = await result.get_data()

                # Step 6: J5 Claim verification against computed facts
                verified_text, claims = await verify_claims(str(full_text), facts_table)
                yield {"type": "verified_claims", "claims": claims}

        except Exception as err:
            logger.error("Agent execution error", error=str(err))
            yield {"type": "error", "message": str(err)}
            full_text = f"An error occurred: {err!s}"

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        cost = 0.0008  # Estimated token cost per turn for flash
        store.record_cost(session_id, cost)

        yield {
            "type": "done",
            "full_text": full_text,
            "cost_usd": cost,
            "latency_ms": latency,
        }


orchestrator = Orchestrator()
