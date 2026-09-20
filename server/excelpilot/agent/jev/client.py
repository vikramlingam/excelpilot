import asyncio
import time
from typing import Any

from typesafe_sdk import (
    AsyncTypeSafeClient,
    Noul,
    Question,
    SystemOneResponse,
    TypeSafeAuthenticationError,
    TypeSafePermissionDeniedError,
)

from excelpilot.config import settings
from excelpilot.telemetry import logger


class JevClient:
    """Client for Jev with automatic cascade fallback."""

    def __init__(self) -> None:
        self.active_backend: str = "offline"
        self.last_latency_ms: float = 0.0
        self.last_model_served: str = ""
        self._typesafe_client: AsyncTypeSafeClient | None = None
        self._openrouter_client: AsyncTypeSafeClient | None = None

        if settings.typesafe_api_key:
            # Priority 1: Direct TypeSafe endpoint
            self._typesafe_client = AsyncTypeSafeClient(
                api_key=settings.typesafe_api_key,
                base_url=settings.typesafe_base_url or None,
            )

        if settings.openrouter_api_key and settings.jev_fallback_via_openrouter:
            # Priority 2: OpenRouter System One endpoint
            self._openrouter_client = AsyncTypeSafeClient(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api",
            )

    def _sanitize_state(self, state: dict[str, Any]) -> dict[str, Any]:
        # Keep payload small and safe by pruning large samples and sensitive keys
        clean: dict[str, Any] = {}
        for key, value in state.items():
            if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                continue
            if isinstance(value, list) and len(value) > 5:
                clean[key] = value[:5]
            elif isinstance(value, dict):
                clean[key] = {k: v for k, v in list(value.items())[:10]}
            else:
                clean[key] = value
        return clean

    async def ask(
        self, state: dict[str, Any], questions: dict[str, Question]
    ) -> SystemOneResponse | None:
        clean_state = self._sanitize_state(state)

        # Try Priority 1: Direct TypeSafe
        if self._typesafe_client:
            try:
                start = time.perf_counter()
                resp = await asyncio.wait_for(
                    self._typesafe_client.system_one(
                        model=settings.jev_model,
                        state=clean_state,
                        questions=questions,
                    ),
                    timeout=5.0,
                )
                self.last_latency_ms = round((time.perf_counter() - start) * 1000, 2)
                self.active_backend = "typesafe"
                self.last_model_served = getattr(resp, "model", "jev")
                return resp
            except (TypeSafeAuthenticationError, TypeSafePermissionDeniedError) as err:
                logger.warning("TypeSafe direct auth failed, trying fallback", error=str(err))
            except Exception as err:
                logger.warning("TypeSafe direct call failed, trying fallback", error=str(err))

        # Try Priority 2: OpenRouter System One fallback
        if self._openrouter_client:
            try:
                start = time.perf_counter()
                resp = await asyncio.wait_for(
                    self._openrouter_client.system_one(
                        model=settings.jev_model,
                        state=clean_state,
                        questions=questions,
                    ),
                    timeout=5.0,
                )
                self.last_latency_ms = round((time.perf_counter() - start) * 1000, 2)
                self.active_backend = "openrouter"
                self.last_model_served = getattr(resp, "model", "jev")
                return resp
            except Exception as err:
                logger.warning("OpenRouter System One fallback failed", error=str(err))

        # Priority 3: Offline fallback
        self.active_backend = "offline"
        logger.warning("All Jev backends failed. Falling back to deterministic policy.")
        return None

    async def probe(self) -> dict[str, Any]:
        # Quick health probe for status bar and doctor CLI
        test_q = {"probe": Noul(instructions="Is this a test?")}
        test_state = {"type": "health_probe"}

        start = time.perf_counter()
        resp = await self.ask(test_state, test_q)
        latency = round((time.perf_counter() - start) * 1000, 2)

        return {
            "status": "ok" if resp is not None else "offline",
            "backend": self.active_backend,
            "latency_ms": latency,
            "model": self.last_model_served or settings.jev_model,
        }


# Global singleton instance
jev_client = JevClient()
