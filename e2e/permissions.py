from __future__ import annotations

from dataclasses import dataclass

# Discord permission bit values used by the E2E environment gate.
ADMINISTRATOR = 1 << 3
MANAGE_CHANNELS = 1 << 4
VIEW_AUDIT_LOG = 1 << 7
MANAGE_ROLES = 1 << 28


@dataclass(frozen=True, slots=True)
class PermissionCheck:
    name: str
    bit: int
    satisfied: bool


def has_permission(bitfield: int, permission: int) -> bool:
    """Return whether a Discord permission is effectively granted.

    Discord's Administrator permission grants all guild permissions. The caller
    is responsible for supplying the effective member role bitfield.
    """
    return bool(bitfield & ADMINISTRATOR) or bool(bitfield & permission)


def describe_permissions(bitfield: int) -> tuple[PermissionCheck, ...]:
    return tuple(
        PermissionCheck(name, bit, has_permission(bitfield, bit))
        for name, bit in (
            ("Manage Channels", MANAGE_CHANNELS),
            ("Manage Roles", MANAGE_ROLES),
            ("View Audit Log", VIEW_AUDIT_LOG),
        )
    )
