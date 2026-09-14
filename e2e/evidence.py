from __future__ import annotations

from typing import Any

from .discord_client import DiscordClient


async def capture_audit_evidence(
    client: DiscordClient,
    *,
    actor_id: int | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Capture recent audit-log entries when the runner has VIEW_AUDIT_LOG."""
    payload = await client.guild_audit_log(user_id=actor_id, limit=limit)
    return {
        "captured_entries": len(payload.get("audit_log_entries", [])),
        "entries": payload.get("audit_log_entries", []),
        "users": payload.get("users", []),
        "application_commands": payload.get("application_commands", []),
    }


def audit_entry_ids(evidence: dict[str, Any]) -> set[int]:
    return {
        int(entry["id"])
        for entry in evidence.get("entries", [])
        if isinstance(entry, dict) and str(entry.get("id", "")).isdigit()
    }
