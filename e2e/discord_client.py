from __future__ import annotations

import asyncio
import random
from collections.abc import Iterable
from typing import Any

import httpx

from .pacing import MutationPacer, PacingConfig


class DiscordAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class DiscordClient:
    """Small REST client restricted to one configured guild."""

    API_BASE = "https://discord.com/api/v10"
    TRANSIENT = {429, 500, 502, 503, 504}

    def __init__(self, token: str, guild_id: int, *, timeout: float = 20.0, max_retries: int = 5, pacing: PacingConfig | None = None) -> None:
        self.guild_id = guild_id
        self.max_retries = max_retries
        self.pacer = MutationPacer(pacing or PacingConfig())
        self._http = httpx.AsyncClient(
            base_url=self.API_BASE,
            timeout=timeout,
            headers={"Authorization": f"Bot {token}", "User-Agent": "school-discord-manager-e2e/0.1"},
        )

    async def __aenter__(self) -> "DiscordClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    def _assert_guild(self, guild_id: int) -> None:
        if guild_id != self.guild_id:
            raise ValueError(f"Guild scope violation: {guild_id} != configured {self.guild_id}")

    async def request(self, method: str, path: str, *, guild_id: int | None = None, **kwargs: Any) -> Any:
        if guild_id is not None:
            self._assert_guild(guild_id)

        is_mutation = method.upper() in {"POST", "PATCH", "PUT", "DELETE"}

        async def do_request() -> httpx.Response:
            for attempt in range(self.max_retries + 1):
                response = await self._http.request(method, path, **kwargs)
                if response.status_code not in self.TRANSIENT or attempt == self.max_retries:
                    return response

                retry_after: float | None = None
                if response.status_code == 429:
                    self.pacer.note_rate_limit()
                    header = response.headers.get("Retry-After")
                    if header:
                        try:
                            retry_after = float(header)
                        except ValueError:
                            retry_after = None
                    try:
                        retry_after = retry_after or float(response.json().get("retry_after", 0))
                    except (ValueError, TypeError):
                        pass

                delay = retry_after if retry_after is not None else min(8.0, 0.5 * (2**attempt))
                delay += random.uniform(0, 0.2)
                await asyncio.sleep(delay)

            raise AssertionError("unreachable")

        if is_mutation:
            async with self.pacer.mutation():
                response = await do_request()
        else:
            response = await do_request()

        if response.is_error:
            detail = response.text[:1000]
            retry_after = None
            if response.status_code == 429:
                try:
                    retry_after = float(response.json().get("retry_after", 0))
                except (ValueError, TypeError):
                    pass
            raise DiscordAPIError(
                response.status_code,
                f"Discord API {response.status_code}: {detail}",
                retry_after=retry_after,
            )

        if is_mutation:
            self.pacer.note_success()

        if response.status_code == 204:
            return None
        return response.json()

    async def current_user(self) -> dict[str, Any]:
        return await self.request("GET", "/users/@me")

    async def guild(self) -> dict[str, Any]:
        return await self.request("GET", f"/guilds/{self.guild_id}", guild_id=self.guild_id)

    async def guild_roles(self) -> list[dict[str, Any]]:
        return await self.request("GET", f"/guilds/{self.guild_id}/roles", guild_id=self.guild_id)

    async def guild_channels(self) -> list[dict[str, Any]]:
        return await self.request("GET", f"/guilds/{self.guild_id}/channels", guild_id=self.guild_id)

    async def guild_member(self, user_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/guilds/{self.guild_id}/members/{user_id}", guild_id=self.guild_id)

    async def create_role(self, *, name: str, permissions: str = "0", reason: str | None = None) -> dict[str, Any]:
        return await self.request("POST", f"/guilds/{self.guild_id}/roles", guild_id=self.guild_id,
                                  params={"reason": reason} if reason else None,
                                  json={"name": name, "permissions": permissions})

    async def create_category(self, *, name: str, reason: str | None = None) -> dict[str, Any]:
        return await self.request("POST", f"/guilds/{self.guild_id}/channels", guild_id=self.guild_id,
                                  params={"reason": reason} if reason else None,
                                  json={"name": name, "type": 4})

    async def create_text_channel(self, *, name: str, parent_id: int | None = None, reason: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "type": 0}
        if parent_id is not None:
            payload["parent_id"] = str(parent_id)
        return await self.request("POST", f"/guilds/{self.guild_id}/channels", guild_id=self.guild_id,
                                  params={"reason": reason} if reason else None, json=payload)

    async def delete_resource(self, resource_id: int, *, reason: str | None = None) -> None:
        await self.request("DELETE", f"/channels/{resource_id}",
                           params={"reason": reason} if reason else None)

    async def delete_role(self, role_id: int, *, reason: str | None = None) -> None:
        await self.request("DELETE", f"/guilds/{self.guild_id}/roles/{role_id}", guild_id=self.guild_id,
                           params={"reason": reason} if reason else None)

    @staticmethod
    def role_ids(member: dict[str, Any]) -> Iterable[int]:
        return (int(role_id) for role_id in member.get("roles", []))
