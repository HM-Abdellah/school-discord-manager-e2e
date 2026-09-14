from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Awaitable, Callable

from .assertions import assert_guild_identity, assert_unique_role_names
from .config import Settings
from .discord_client import DiscordClient, DiscordAPIError
from .fixtures import FixtureManager
from .models import TestResult
from .reporting import Reporter
from .run_lock import RunAlreadyActive, RunLock
from .snapshots import snapshot_guild, snapshot_to_dict

TestFn = Callable[[], Awaitable[tuple[str, dict]]]


class Runner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @classmethod
    def from_environment(cls) -> "Runner":
        return cls(Settings.from_environment())

    async def cli(self, argv: list[str]) -> int:
        parser = argparse.ArgumentParser(prog="python -m e2e")
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("snapshot")
        run_parser = sub.add_parser("run")
        run_parser.add_argument("--suite", default=None)
        run_parser.add_argument("--test", default=None)
        run_parser.add_argument("--destructive", action="store_true")
        sub.add_parser("cleanup")
        args = parser.parse_args(argv)
        command = args.command or "run"
        if command == "snapshot":
            return await self.snapshot_command()
        if command == "cleanup":
            return await self.cleanup_command()
        return await self.run_command(args)

    def _client(self) -> DiscordClient:
        return DiscordClient(
            self.settings.discord_token,
            self.settings.guild_id,
            timeout=self.settings.request_timeout,
            max_retries=self.settings.max_retries,
            pacing=self.settings.pacing,
        )

    async def snapshot_command(self) -> int:
        async with self._client() as client:
            snapshot = await snapshot_guild(client)
            self.settings.report_dir.mkdir(parents=True, exist_ok=True)
            path = self.settings.report_dir / "snapshot.json"
            path.write_text(
                json.dumps(snapshot_to_dict(snapshot), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Snapshot written to {path}")
        return 0

    async def cleanup_command(self) -> int:
        async with self._client() as client:
            fixtures = FixtureManager(client, self.settings.fixture_manifest)
            for message in await fixtures.cleanup():
                print(message)
        return 0

    async def run_command(self, args: argparse.Namespace) -> int:
        if args.destructive and not self.settings.destructive_allowed:
            print("Destructive mode blocked: set E2E_ALLOW_DESTRUCTIVE=true first.")
            return 2

        lock = RunLock(self.settings.fixture_manifest.parent / "run.lock")
        try:
            lock.acquire()
        except RunAlreadyActive as exc:
            print(f"Run blocked: {exc}")
            return 2

        start = time.perf_counter()
        results: list[TestResult] = []
        try:
            async with self._client() as client:
                environment_ok = await self._record(
                    results,
                    "Environment sanity",
                    lambda: self._environment(client),
                )
                if environment_ok:
                    await self._record(
                        results,
                        "REST observation baseline",
                        lambda: self._baseline(client),
                    )
                else:
                    results.append(
                        TestResult(
                            "Command-driven suites",
                            "skipped",
                            0.0,
                            "Environment sanity failed",
                        )
                    )
        finally:
            lock.release()

        duration = time.perf_counter() - start
        reporter = Reporter(self.settings.report_dir)
        reporter.console_report(results)
        reporter.write_json(results, duration)
        reporter.write_html(results, duration)
        return 0 if all(r.status != "failed" for r in results) else 1

    async def _record(self, results: list[TestResult], name: str, fn: TestFn) -> bool:
        start = time.perf_counter()
        try:
            message, details = await fn()
            results.append(
                TestResult(
                    name,
                    "passed",
                    time.perf_counter() - start,
                    message,
                    details,
                )
            )
            return True
        except Exception as exc:  # noqa: BLE001
            results.append(
                TestResult(
                    name,
                    "failed",
                    time.perf_counter() - start,
                    f"{type(exc).__name__}: {exc}",
                )
            )
            return False

    async def _environment(self, client: DiscordClient) -> tuple[str, dict]:
        me = await client.current_user()
        guild = await client.guild()
        roles = await client.guild_roles()
        member = await client.guild_member(int(me["id"]))
        role_map = {int(role["id"]): role for role in roles}
        permissions = 0
        for role_id in member.get("roles", []):
            role = role_map.get(int(role_id))
            if role:
                permissions |= int(role.get("permissions", 0))

        details = {
            "runner_bot_id": int(me["id"]),
            "guild_id": int(guild["id"]),
            "guild_name": guild["name"],
            "runner_role_count": len(member.get("roles", [])),
            "runner_computed_guild_role_permissions": permissions,
        }

        if self.settings.target_bot_id is not None:
            try:
                target = await client.guild_member(self.settings.target_bot_id)
            except DiscordAPIError as exc:
                raise RuntimeError(
                    f"Target School Manager bot {self.settings.target_bot_id} is not a member of the configured guild. "
                    f"Discord returned {exc.status_code}."
                ) from exc
            user = target.get("user", {})
            if not bool(user.get("bot", False)):
                raise RuntimeError(
                    f"TARGET_BOT_ID {self.settings.target_bot_id} resolves to a non-bot account."
                )
            details["target_bot_id"] = self.settings.target_bot_id
            details["target_bot_tag"] = user.get("username")
            details["target_bot_roles"] = [int(role_id) for role_id in target.get("roles", [])]

        snapshot = await snapshot_guild(client)
        assert_guild_identity(snapshot, self.settings.guild_id)
        return "REST access and configured guild scope are valid. Target-bot membership is verified when configured.", details

    async def _baseline(self, client: DiscordClient) -> tuple[str, dict]:
        snapshot = await snapshot_guild(client)
        assert_unique_role_names(snapshot)
        return "Baseline snapshot captured; no command was invoked by the runner.", {
            "roles": len(snapshot.roles),
            "channels": len(snapshot.channels),
            "captured_at": snapshot.captured_at,
        }
