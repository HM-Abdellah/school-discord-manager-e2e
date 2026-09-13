from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class RoleState:
    id: int
    name: str
    position: int
    permissions: int
    managed: bool
    mentionable: bool


@dataclass(frozen=True, slots=True)
class ChannelState:
    id: int
    name: str
    type: int
    parent_id: int | None
    position: int
    permission_overwrites: tuple[tuple[int, int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class GuildSnapshot:
    guild_id: int
    guild_name: str
    owner_id: int
    roles: tuple[RoleState, ...]
    channels: tuple[ChannelState, ...]
    captured_at: str


@dataclass(frozen=True, slots=True)
class FixtureResource:
    kind: Literal["role", "category", "channel"]
    id: int
    name: str


@dataclass(slots=True)
class FixtureRegistry:
    resources: list[FixtureResource] = field(default_factory=list)

    def add(self, resource: FixtureResource) -> None:
        if not any(r.kind == resource.kind and r.id == resource.id for r in self.resources):
            self.resources.append(resource)

    def remove(self, resource_id: int) -> None:
        self.resources = [r for r in self.resources if r.id != resource_id]

    def to_json(self) -> dict[str, Any]:
        return {"resources": [asdict(r) for r in self.resources]}

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "FixtureRegistry":
        return cls([FixtureResource(**item) for item in payload.get("resources", [])])


@dataclass(frozen=True, slots=True)
class TestResult:
    name: str
    status: Literal["passed", "failed", "skipped", "warning"]
    duration_seconds: float
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SnapshotDiff:
    created: dict[str, list[int]]
    deleted: dict[str, list[int]]
    modified: dict[str, list[int]]
    unchanged: dict[str, list[int]]
    unexpected: dict[str, list[int]]
    missing: dict[str, list[int]]
