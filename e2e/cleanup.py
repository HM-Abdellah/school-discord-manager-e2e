from __future__ import annotations

from .fixtures import FixtureManager


async def cleanup_fixtures(fixtures: FixtureManager) -> list[str]:
    return await fixtures.cleanup()
