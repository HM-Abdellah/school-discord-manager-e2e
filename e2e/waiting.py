from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from .discord_client import DiscordClient

T = TypeVar("T")


async def wait_until(
    predicate: Callable[[], Awaitable[T | None]],
    *,
    timeout: float,
    interval: float,
    description: str,
) -> T:
    """Poll until a predicate returns a non-None value."""
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


async def wait_for_role(
    client: DiscordClient,
    role_id: int,
    *,
    timeout: float,
    interval: float,
) -> dict[str, Any]:
    async def find() -> dict[str, Any] | None:
        roles = await client.guild_roles()
        return next((role for role in roles if int(role["id"]) == role_id), None)

    return await wait_until(
        find,
        timeout=timeout,
        interval=interval,
        description=f"role {role_id}",
    )


async def wait_for_channel(
    client: DiscordClient,
    channel_id: int,
    *,
    timeout: float,
    interval: float,
) -> dict[str, Any]:
    async def find() -> dict[str, Any] | None:
        channels = await client.guild_channels()
        return next((channel for channel in channels if int(channel["id"]) == channel_id), None)

    return await wait_until(
        find,
        timeout=timeout,
        interval=interval,
        description=f"channel {channel_id}",
    )


async def wait_for_channel_absent(
    client: DiscordClient,
    channel_id: int,
    *,
    timeout: float,
    interval: float,
) -> None:
    async def gone() -> bool | None:
        channels = await client.guild_channels()
        return True if all(int(channel["id"]) != channel_id for channel in channels) else None

    await wait_until(
        gone,
        timeout=timeout,
        interval=interval,
        description=f"channel {channel_id} to disappear",
    )


async def wait_for_role_absent(
    client: DiscordClient,
    role_id: int,
    *,
    timeout: float,
    interval: float,
) -> None:
    async def gone() -> bool | None:
        roles = await client.guild_roles()
        return True if all(int(role["id"]) != role_id for role in roles) else None

    await wait_until(
        gone,
        timeout=timeout,
        interval=interval,
        description=f"role {role_id} to disappear",
    )


async def wait_for_member_roles(
    client: DiscordClient,
    user_id: int,
    expected_role_ids: set[int],
    *,
    timeout: float,
    interval: float,
) -> dict[str, Any]:
    async def find() -> dict[str, Any] | None:
        member = await client.guild_member(user_id)
        current = {int(role_id) for role_id in member.get("roles", [])}
        return member if expected_role_ids.issubset(current) else None

    return await wait_until(
        find,
        timeout=timeout,
        interval=interval,
        description=f"member {user_id} to have roles {sorted(expected_role_ids)}",
    )
