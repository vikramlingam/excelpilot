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

_AUTH_COOLDOWN_S = 15 * 60
_TRANSIENT_COOLDOWN_S = 30
_VERDICT_TTL_S = 120.0
_VERDICT_MAX = 256


class JevClient:
    """Jev / System One client with TypeSafe -> OpenRouter -> offline cascade."""

    def __init__(self) -> None:
        self.active_backend: str = "unprobed"
        self.last_latency_ms: float = 0.0
        self.last_model_served: str = ""
        self.last_error: str = ""
        self._typesafe_client: AsyncTypeSafeClient | None = None
        self._openrouter_client: AsyncTypeSafeClient | None = None
        self._skip_typesafe_until: float = 0.0
        # Same question about the same state within 2 minutes → reuse the verdict.
        self._verdict_cache: dict[str, tuple[float, SystemOneResponse]] = {}
        self.cache_hits: int = 0
        self.calls: int = 0

        if settings.typesafe_api_key:
            kwargs: dict[str, Any] = {"api_key": settings.typesafe_api_key}
            if settings.typesafe_base_url:
                kwargs["base_url"] = settings.typesafe_base_url
            self._typesafe_client = AsyncTypeSafeClient(**kwargs)

        if settings.openrouter_api_key and settings.jev_fallback_via_openrouter:
            self._openrouter_client = AsyncTypeSafeClient(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api",
            )

    def status_snapshot(self) -> dict[str, Any]:
        backend = self.active_backend
        status = "ok" if backend in {"typesafe", "openrouter"} else backend
        return {
            "status": status,
            "backend": backend,
            "latency_ms": self.last_latency_ms,
            "model": self.last_model_served or settings.jev_model,
            "error": self.last_error,
            "calls": self.calls,
            "cache_hits": self.cache_hits,
        }

    @staticmethod
    def _cache_key(state: dict[str, Any], questions: dict[str, Question]) -> str:
        import hashlib
        import json

        try:
            q = {k: getattr(v, "instructions", str(v)) for k, v in questions.items()}
            raw = json.dumps({"s": state, "q": q}, sort_keys=True, default=str)
        except Exception:
            raw = repr((state, list(questions)))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _sanitize_state(self, state: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in state.items():
            lowered = key.lower()
            if any(tok in lowered for tok in ("key", "secret", "token", "password")):
                continue
            if isinstance(value, list) and len(value) > 5:
                clean[key] = value[:5]
            elif isinstance(value, dict):
                clean[key] = {k: v for k, v in list(value.items())[:10]}
            elif isinstance(value, str) and len(value) > 2000:
                clean[key] = value[:2000]
            else:
                clean[key] = value
        return clean

    def _disable_typesafe(self, seconds: float, reason: str) -> None:
        self._skip_typesafe_until = time.monotonic() + seconds
        self.last_error = reason
        logger.warning("Skipping TypeSafe Jev backend", seconds=seconds, reason=reason)

    async def _call(
        self,
        client: AsyncTypeSafeClient,
        backend: str,
        state: dict[str, Any],
        questions: dict[str, Question],
        timeout: float,
    ) -> SystemOneResponse:
        start = time.perf_counter()
        resp = await asyncio.wait_for(
            client.system_one(model=settings.jev_model, state=state, questions=questions),
            timeout=timeout,
        )
        self.last_latency_ms = round((time.perf_counter() - start) * 1000, 2)
        self.active_backend = backend
        self.last_model_served = getattr(resp, "model", "jev")
        self.last_error = ""
        return resp

    async def ask(
        self, state: dict[str, Any], questions: dict[str, Question]
    ) -> SystemOneResponse | None:
        clean_state = self._sanitize_state(state)
        now = time.monotonic()

        key = self._cache_key(clean_state, questions)
        cached = self._verdict_cache.get(key)
        if cached and (now - cached[0]) < _VERDICT_TTL_S:
            self.cache_hits += 1
            return cached[1]

        resp = await self._ask_uncached(clean_state, questions, now)
        if resp is not None:
            if len(self._verdict_cache) >= _VERDICT_MAX:
                oldest = min(self._verdict_cache, key=lambda k: self._verdict_cache[k][0])
                self._verdict_cache.pop(oldest, None)
            self._verdict_cache[key] = (time.monotonic(), resp)
        return resp

    async def _ask_uncached(
        self, clean_state: dict[str, Any], questions: dict[str, Question], now: float
    ) -> SystemOneResponse | None:
        self.calls += 1

        if self._typesafe_client and now >= self._skip_typesafe_until:
            try:
                return await self._call(
                    self._typesafe_client,
                    "typesafe",
                    clean_state,
                    questions,
                    settings.jev_typesafe_timeout_s,
                )
            except (TypeSafeAuthenticationError, TypeSafePermissionDeniedError) as err:
                self._disable_typesafe(_AUTH_COOLDOWN_S, f"auth: {err}")
            except TimeoutError:
                self._disable_typesafe(_TRANSIENT_COOLDOWN_S, "typesafe timeout")
            except Exception as err:
                self._disable_typesafe(_TRANSIENT_COOLDOWN_S, str(err))

        if self._openrouter_client:
            try:
                return await self._call(
                    self._openrouter_client,
                    "openrouter",
                    clean_state,
                    questions,
                    settings.jev_openrouter_timeout_s,
                )
            except Exception as err:
                self.last_error = str(err)
                logger.warning("OpenRouter System One failed", error=str(err))

        self.active_backend = "offline"
        logger.warning("All Jev backends unavailable; using deterministic policy")
        return None

    async def probe(self) -> dict[str, Any]:
        await self.ask(
            {"type": "health_probe"},
            {"probe": Noul(instructions="Is this a connectivity probe?")},
        )
        return self.status_snapshot()


jev_client = JevClient()
