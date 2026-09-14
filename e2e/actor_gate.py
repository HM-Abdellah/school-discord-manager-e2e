from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .discord_client import DiscordClient
from .evidence import capture_audit_evidence
from .models import GuildSnapshot, SnapshotDiff
from .snapshots import compare_snapshots, snapshot_guild
from .waiting import wait_until


@dataclass(frozen=True, slots=True)
class ManualActorCheckpoint:
    instruction: str
    before: GuildSnapshot
    before_audit: dict[str, Any] | None


class ManualActorGate:
    """Human-in-the-loop bridge for real Discord command invocation.

    This never logs in as a user and never fabricates an interaction. The human
    actor performs the command in the normal Discord client; the runner observes
    the resulting state transition.
    """

    def __init__(self, client: DiscordClient, *, timeout: float, interval: float) -> None:
        self.client = client
        self.timeout = timeout
        self.interval = interval

    async def checkpoint(self, instruction: str, *, actor_id: int | None = None) -> ManualActorCheckpoint:
        before = await snapshot_guild(self.client)
        try:
            audit = await capture_audit_evidence(self.client, actor_id=actor_id)
        except Exception:
            audit = None
        print(f"\n[ACTION REQUIRED] {instruction}")
        await asyncio.to_thread(input, "Press Enter after the actor has completed the action... ")
        return ManualActorCheckpoint(instruction, before, audit)

    async def wait_for_change(
        self,
        checkpoint: ManualActorCheckpoint,
        *,
        description: str,
        require_diff: bool = True,
    ) -> tuple[GuildSnapshot, SnapshotDiff]:
        async def changed() -> GuildSnapshot | None:
            current = await snapshot_guild(self.client)
            diff = compare_snapshots(checkpoint.before, current)
            if require_diff and not any(
                diff_map.get(kind)
                for diff_map in (diff.created, diff.deleted, diff.modified)
                for kind in ("roles", "channels")
            ):
                return None
            return current

        after = await wait_until(
            changed,
            timeout=self.timeout,
            interval=self.interval,
            description=description,
        )
        return after, compare_snapshots(checkpoint.before, after)
