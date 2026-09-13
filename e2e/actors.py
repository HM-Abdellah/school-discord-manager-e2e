"""Actor metadata boundary.

This module does not automate regular Discord user accounts and does not craft
slash-command interaction payloads. Actor invocation will be added only through
a supported Discord interaction model.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Actor:
    name: str
    user_id: int
    expected_roles: tuple[str, ...] = ()
    allowed_commands: tuple[str, ...] = ()
    forbidden_commands: tuple[str, ...] = ()
