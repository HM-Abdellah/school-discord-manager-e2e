from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def wait_until(predicate: Callable[[], Awaitable[T | None]], *, timeout: float, interval: float, description: str) -> T:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            value = await predicate()
            if value is not None:
                return value
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        await asyncio.sleep(interval)
    suffix = f" Last error: {type(last_error).__name__}: {last_error}" if last_error else ""
    raise TimeoutError(f"Timed out waiting for {description}.{suffix}")
