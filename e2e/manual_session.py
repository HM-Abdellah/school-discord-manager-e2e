from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .actor_gate import ManualActorGate
from .assertions import assert_guild_identity
from .config import Settings
from .discord_client import DiscordClient
from .evidence import capture_audit_evidence
from .snapshots import snapshot_to_dict


@dataclass(frozen=True, slots=True)
class ManualSessionResult:
    scenario_id: str
    instruction: str
    actor_id: int | None
    started_at: float
    finished_at: float
    before_snapshot: str
    after_snapshot: str
    diff: dict[str, Any]
    audit_before: dict[str, Any] | None
    audit_after: dict[str, Any] | None


async def run_manual_session(
    settings: Settings,
    *,
    scenario_id: str,
    instruction: str,
    actor_id: int | None = None,
    expect_change: bool = True,
) -> ManualSessionResult:
    """Observe one human-executed Discord scenario without impersonating the actor."""
    started = time.time()
    output_dir = settings.report_dir / "manual" / scenario_id
    output_dir.mkdir(parents=True, exist_ok=True)

    async with DiscordClient(
        settings.discord_token,
        settings.guild_id,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
        pacing=settings.pacing,
    ) as client:
        gate = ManualActorGate(
            client,
            timeout=settings.request_timeout,
            interval=settings.poll_interval,
        )

        checkpoint = await gate.checkpoint(instruction, actor_id=actor_id)
        before_dict = snapshot_to_dict(checkpoint.before)
        assert_guild_identity(checkpoint.before, settings.guild_id)
        before_path = output_dir / "before.json"
        before_path.write_text(
            json.dumps(before_dict, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        if expect_change:
            after, diff = await gate.wait_for_change(
                checkpoint,
                description=f"a Discord state change for {scenario_id}",
                require_diff=True,
            )
        else:
            # Give Discord a short settling interval after the human action, then
            # capture the state without requiring a resource mutation.
            await __import__("asyncio").sleep(settings.poll_interval)
            after = await __import__("e2e.snapshots", fromlist=["snapshot_guild"]).snapshot_guild(client)
            diff = __import__("e2e.snapshots", fromlist=["compare_snapshots"]).compare_snapshots(
                checkpoint.before, after
            )

        after_path = output_dir / "after.json"
        after_path.write_text(
            json.dumps(snapshot_to_dict(after), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        try:
            audit_after = await capture_audit_evidence(client, actor_id=actor_id)
        except Exception:
            audit_after = None

    finished = time.time()
    result = ManualSessionResult(
        scenario_id=scenario_id,
        instruction=instruction,
        actor_id=actor_id,
        started_at=started,
        finished_at=finished,
        before_snapshot=str(before_path),
        after_snapshot=str(after_path),
        diff=asdict(diff),
        audit_before=checkpoint.before_audit,
        audit_after=audit_after,
    )
    (output_dir / "result.json").write_text(
        json.dumps(asdict(result), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result
