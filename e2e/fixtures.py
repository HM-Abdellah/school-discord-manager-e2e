from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .discord_client import DiscordClient
from .models import FixtureRegistry, FixtureResource


class FixtureManager:
    """Own and clean up only resources recorded by this runner."""

    def __init__(self, client: DiscordClient, manifest: Path) -> None:
        self.client = client
        self.manifest = manifest
        self.registry = self._load()

    def _load(self) -> FixtureRegistry:
        if not self.manifest.exists():
            return FixtureRegistry()
        try:
            payload: Any = json.loads(self.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Fixture manifest is unreadable: {self.manifest}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"Fixture manifest must contain a JSON object: {self.manifest}")
        return FixtureRegistry.from_json(payload)

    def save(self) -> None:
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        temp = self.manifest.with_suffix(self.manifest.suffix + ".tmp")
        temp.write_text(
            json.dumps(self.registry.to_json(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp.replace(self.manifest)

    async def create_custom_category(self, name: str) -> FixtureResource:
        raw = await self.client.create_category(name=name, reason="School Manager E2E fixture")
        item = FixtureResource("category", int(raw["id"]), str(raw["name"]))
        self.registry.add(item)
        self.save()
        return item

    async def create_custom_channel(self, name: str, *, parent_id: int | None = None) -> FixtureResource:
        raw = await self.client.create_text_channel(
            name=name, parent_id=parent_id, reason="School Manager E2E fixture"
        )
        item = FixtureResource("channel", int(raw["id"]), str(raw["name"]))
        self.registry.add(item)
        self.save()
        return item

    async def create_custom_role(self, name: str) -> FixtureResource:
        raw = await self.client.create_role(name=name, reason="School Manager E2E fixture")
        item = FixtureResource("role", int(raw["id"]), str(raw["name"]))
        self.registry.add(item)
        self.save()
        return item

    async def _current_ids(self) -> tuple[set[int], set[int]]:
        channels = await self.client.guild_channels()
        roles = await self.client.guild_roles()
        return (
            {int(channel["id"]) for channel in channels},
            {int(role["id"]) for role in roles},
        )

    async def cleanup(self) -> list[str]:
        """Delete owned fixtures only; keep failures for a later retry."""
        messages: list[str] = []
        remaining: list[FixtureResource] = []
        channel_ids, role_ids = await self._current_ids()

        channels = [resource for resource in self.registry.resources if resource.kind == "channel"]
        categories = [resource for resource in self.registry.resources if resource.kind == "category"]
        roles = [resource for resource in self.registry.resources if resource.kind == "role"]

        # Children first, then their categories, then roles.
        ordered = list(reversed(channels)) + list(reversed(categories)) + list(reversed(roles))

        for resource in ordered:
            try:
                if resource.kind == "role":
                    if resource.id not in role_ids:
                        messages.append(f"already absent role {resource.id} ({resource.name})")
                    else:
                        await self.client.delete_role(
                            resource.id,
                            reason="School Manager E2E fixture cleanup",
                        )
                        messages.append(f"deleted role {resource.id} ({resource.name})")
                        role_ids.discard(resource.id)
                else:
                    # A channel/category can only be targeted when we have observed
                    # the exact ID in this configured guild. This blocks stale-ID drift.
                    if resource.id not in channel_ids:
                        messages.append(f"already absent {resource.kind} {resource.id} ({resource.name})")
                    else:
                        await self.client.delete_resource(
                            resource.id,
                            reason="School Manager E2E fixture cleanup",
                        )
                        messages.append(f"deleted {resource.kind} {resource.id} ({resource.name})")
                        channel_ids.discard(resource.id)
            except Exception as exc:  # noqa: BLE001
                remaining.append(resource)
                messages.append(
                    f"cleanup warning for {resource.kind} {resource.id}: "
                    f"{type(exc).__name__}: {exc}"
                )

        # Rebuild the manifest only from resources that actually failed. Resources
        # that were already absent are intentionally considered clean.
        self.registry.resources = remaining
        self.save()
        return messages
