from __future__ import annotations

import asyncio
import random
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


class RateLimitSafetyStop(RuntimeError):
    """Raised when repeated rate limits make continuing the run unsafe."""


@dataclass(frozen=True, slots=True)
class PacingConfig:
    min_mutation_delay: float = 2.0
    max_jitter: float = 2.5
    max_consecutive_mutations: int = 5
    cooldown_after_batch: float = 5.0
    max_rate_limit_events: int = 3


class MutationPacer:
    """Serialize guild mutations with conservative, non-evasive pacing."""

    def __init__(self, config: PacingConfig) -> None:
        self.config = config
        self._lock = asyncio.Lock()
        self._last_mutation_at = 0.0
        self._consecutive_mutations = 0
        self._rate_limit_events = 0

    @asynccontextmanager
    async def mutation(self) -> AsyncIterator[None]:
        async with self._lock:
            now = time.monotonic()
            delay = self.config.min_mutation_delay - (now - self._last_mutation_at)
            if delay > 0:
                await asyncio.sleep(delay)

            if self._consecutive_mutations >= self.config.max_consecutive_mutations:
                await asyncio.sleep(self.config.cooldown_after_batch)
                self._consecutive_mutations = 0

            try:
                yield
            finally:
                self._last_mutation_at = time.monotonic()
                self._consecutive_mutations += 1
                jitter = random.uniform(0.0, self.config.max_jitter)
                if jitter:
                    await asyncio.sleep(jitter)

    def note_rate_limit(self) -> None:
        self._rate_limit_events += 1
        if self._rate_limit_events >= self.config.max_rate_limit_events:
            raise RateLimitSafetyStop(
                f"Observed {self._rate_limit_events} rate-limit responses; stopping safely."
            )

    def note_success(self) -> None:
        self._rate_limit_events = max(0, self._rate_limit_events - 1)
