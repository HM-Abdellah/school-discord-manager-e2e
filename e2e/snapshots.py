from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .discord_client import DiscordClient
from .models import ChannelState, GuildSnapshot, RoleState, SnapshotDiff


async def snapshot_guild(client: DiscordClient) -> GuildSnapshot:
    guild = await client.guild()
    roles_raw = await client.guild_roles()
    channels_raw = await client.guild_channels()

    roles = tuple(sorted((RoleState(
        id=int(role["id"]), name=str(role["name"]), position=int(role["position"]),
        permissions=int(role.get("permissions", 0)), managed=bool(role.get("managed", False)),
        mentionable=bool(role.get("mentionable", False)),
    ) for role in roles_raw), key=lambda item: item.id))

    channels = tuple(sorted((ChannelState(
        id=int(channel["id"]), name=str(channel["name"]), type=int(channel["type"]),
        parent_id=int(channel["parent_id"]) if channel.get("parent_id") else None,
        position=int(channel.get("position", 0)),
        permission_overwrites=tuple(sorted((
            (int(ow["id"]), int(ow.get("allow", "0")), int(ow.get("deny", "0")))
            for ow in channel.get("permission_overwrites", [])
        ))),
    ) for channel in channels_raw), key=lambda item: item.id))

    return GuildSnapshot(
        guild_id=int(guild["id"]), guild_name=str(guild["name"]), owner_id=int(guild["owner_id"]),
        roles=roles, channels=channels, captured_at=datetime.now(timezone.utc).isoformat(),
    )


def snapshot_to_dict(snapshot: GuildSnapshot) -> dict[str, Any]:
    return {
        "guild_id": snapshot.guild_id,
        "guild_name": snapshot.guild_name,
        "owner_id": snapshot.owner_id,
        "captured_at": snapshot.captured_at,
        "roles": [{
            "id": x.id, "name": x.name, "position": x.position,
            "permissions": x.permissions, "managed": x.managed, "mentionable": x.mentionable,
        } for x in snapshot.roles],
        "channels": [{
            "id": x.id, "name": x.name, "type": x.type, "parent_id": x.parent_id,
            "position": x.position, "permission_overwrites": [list(v) for v in x.permission_overwrites],
        } for x in snapshot.channels],
    }


def compare_snapshots(before: GuildSnapshot, after: GuildSnapshot) -> SnapshotDiff:
    def compare(before_items: list[Any], after_items: list[Any]) -> tuple[list[int], list[int], list[int], list[int]]:
        b = {item.id: item for item in before_items}
        a = {item.id: item for item in after_items}
        created = sorted(set(a) - set(b))
        deleted = sorted(set(b) - set(a))
        unchanged = sorted(i for i in set(a) & set(b) if a[i] == b[i])
        modified = sorted(i for i in set(a) & set(b) if a[i] != b[i])
        return created, deleted, modified, unchanged

    rc, rd, rm, ru = compare(list(before.roles), list(after.roles))
    cc, cd, cm, cu = compare(list(before.channels), list(after.channels))
    return SnapshotDiff(
        created={"roles": rc, "channels": cc}, deleted={"roles": rd, "channels": cd},
        modified={"roles": rm, "channels": cm}, unchanged={"roles": ru, "channels": cu},
        unexpected={"roles": [], "channels": []}, missing={"roles": [], "channels": []},
    )
