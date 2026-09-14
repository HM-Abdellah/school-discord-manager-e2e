from __future__ import annotations

import asyncio
from pathlib import Path

from e2e.command_catalog import get_command
from e2e.models import ChannelState, GuildSnapshot, RoleState
from e2e.pacing import MutationPacer, PacingConfig
from e2e.run_lock import RunAlreadyActive, RunLock
from e2e.snapshots import compare_snapshots


def _snapshot(role_count: int = 1, *, channel_name: str = "general") -> GuildSnapshot:
    roles = tuple(
        RoleState(i, f"role-{i}", i, 0, False, False) for i in range(1, role_count + 1)
    )
    channels = (
        ChannelState(100, channel_name, 0, None, 0, ()),
    )
    return GuildSnapshot(1, "test", 999, roles, channels, "now")


def test_snapshot_diff_classifies_changes() -> None:
    before = _snapshot()
    after = _snapshot(role_count=2, channel_name="renamed")
    diff = compare_snapshots(before, after)

    assert diff.created["roles"] == [2]
    assert diff.modified["channels"] == [100]
    assert diff.unchanged["roles"] == [1]


def test_command_catalog_marks_reset_destructive() -> None:
    command = get_command("/resetserver")
    assert command.destructive is True
    assert command.invocation == "manual-actor"


def test_run_lock_blocks_second_owner(tmp_path: Path) -> None:
    path = tmp_path / "run.lock"
    first = RunLock(path)
    second = RunLock(path)
    first.acquire()
    try:
        try:
            second.acquire()
        except RunAlreadyActive:
            pass
        else:
            raise AssertionError("second lock unexpectedly acquired")
    finally:
        first.release()


def test_mutation_pacer_serializes_mutations() -> None:
    async def exercise() -> None:
        pacer = MutationPacer(
            PacingConfig(
                min_mutation_delay=0,
                max_jitter=0,
                max_consecutive_mutations=2,
                cooldown_after_batch=0,
            )
        )
        async with pacer.mutation():
            pass
        async with pacer.mutation():
            pass

    asyncio.run(exercise())
