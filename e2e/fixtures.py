from __future__ import annotations

import json
from pathlib import Path

from .discord_client import DiscordClient
from .models import FixtureRegistry, FixtureResource


class FixtureManager:
    def __init__(self, client: DiscordClient, manifest: Path) -> None:
        self.client = client
        self.manifest = manifest
        self.registry = self._load()

    def _load(self) -> FixtureRegistry:
        if not self.manifest.exists():
            return FixtureRegistry()
        return FixtureRegistry.from_json(json.loads(self.manifest.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        self.manifest.write_text(json.dumps(self.registry.to_json(), indent=2), encoding="utf-8")

    async def create_custom_category(self, name: str) -> FixtureResource:
        raw = await self.client.create_category(name=name, reason="School Manager E2E fixture")
        item = FixtureResource("category", int(raw["id"]), str(raw["name"]))
        self.registry.add(item)
        self.save()
        return item

    async def create_custom_channel(self, name: str, *, parent_id: int | None = None) -> FixtureResource:
        raw = await self.client.create_text_channel(name=name, parent_id=parent_id, reason="School Manager E2E fixture")
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

    async def cleanup(self) -> list[str]:
        messages: list[str] = []
        # Exact registered IDs only. Channels/categories first, roles last.
        channels = [r for r in self.registry.resources if r.kind != "role"]
        roles = [r for r in self.registry.resources if r.kind == "role"]
        for resource in reversed(channels) + reversed(roles):
            try:
                if resource.kind == "role":
                    await self.client.delete_role(resource.id, reason="School Manager E2E fixture cleanup")
                else:
                    await self.client.delete_resource(resource.id, reason="School Manager E2E fixture cleanup")
                messages.append(f"deleted {resource.kind} {resource.id} ({resource.name})")
            except Exception as exc:  # noqa: BLE001
                messages.append(f"cleanup warning for {resource.kind} {resource.id}: {type(exc).__name__}: {exc}")
        self.registry = FixtureRegistry()
        self.save()
        return messages
