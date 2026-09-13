from __future__ import annotations

from typing import Any

from .models import GuildSnapshot


class AssertionFailure(AssertionError):
    pass


def assert_guild_identity(snapshot: GuildSnapshot, expected_guild_id: int) -> None:
    if snapshot.guild_id != expected_guild_id:
        raise AssertionFailure(f"Expected guild {expected_guild_id}, got {snapshot.guild_id}")


def assert_unique_role_names(snapshot: GuildSnapshot) -> None:
    names = [role.name for role in snapshot.roles if not role.managed]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise AssertionFailure(f"Duplicate unmanaged role names found: {sorted(duplicates)}")


def assert_fixture_survival(snapshot: GuildSnapshot, fixture_ids: set[int]) -> None:
    present = {channel.id for channel in snapshot.channels} | {role.id for role in snapshot.roles}
    missing = fixture_ids - present
    if missing:
        raise AssertionFailure(f"Runner-owned fixture(s) disappeared unexpectedly: {sorted(missing)}")


def assert_expected_counts(snapshot: GuildSnapshot, *, min_roles: int | None = None, min_channels: int | None = None) -> dict[str, Any]:
    result = {"roles": len(snapshot.roles), "channels": len(snapshot.channels)}
    if min_roles is not None and len(snapshot.roles) < min_roles:
        raise AssertionFailure(f"Expected at least {min_roles} roles, got {len(snapshot.roles)}")
    if min_channels is not None and len(snapshot.channels) < min_channels:
        raise AssertionFailure(f"Expected at least {min_channels} channels, got {len(snapshot.channels)}")
    return result
