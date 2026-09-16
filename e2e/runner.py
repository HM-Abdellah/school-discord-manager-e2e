from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Awaitable, Callable

from .actor_gate import ManualActorGate
from .assertions import assert_guild_identity, assert_unique_role_names
from .command_catalog import get_command
from .config import Settings
from .discord_client import DiscordAPIError, DiscordClient
from .fixtures import FixtureManager
from .models import TestResult
from .permissions import MANAGE_CHANNELS, MANAGE_ROLES, VIEW_AUDIT_LOG, has_permission
from .reporting import Reporter
from .run_lock import RunAlreadyActive, RunLock
from .snapshots import compare_snapshots, snapshot_guild, snapshot_to_dict

TestFn = Callable[[], Awaitable[tuple[str, dict]]]


class Runner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @classmethod
    def from_environment(cls) -> "Runner":
        return cls(Settings.from_environment())

    async def cli(self, argv: list[str]) -> int:
        parser = argparse.ArgumentParser(prog="python -m e2e")
        sub = parser.add_subparsers(dest="subcommand")
        sub.add_parser("snapshot")
        run_parser = sub.add_parser("run")
        run_parser.add_argument("--suite", default=None)
        run_parser.add_argument("--test", default=None)
        run_parser.add_argument("--destructive", action="store_true")
        manual_parser = sub.add_parser(
            "manual",
            help="observe one human-executed Discord scenario",
        )
        manual_parser.add_argument("--scenario", required=True, help="Stable scenario ID, e.g. CORE-001")
        manual_parser.add_argument(
            "--command",
            dest="manager_command",
            default=None,
            help="School Manager command name, e.g. /setup; used for destructive safety checks",
        )
        manual_parser.add_argument(
            "--instruction",
            required=True,
            help="Exact action the human actor must perform in Discord",
        )
        manual_parser.add_argument(
            "--actor-id",
            type=int,
            default=None,
            help="Optional Discord user ID used to correlate audit evidence",
        )
        manual_parser.add_argument(
            "--destructive",
            action="store_true",
            help="Explicitly allow a destructive command after E2E_ALLOW_DESTRUCTIVE=true",
        )
        manual_parser.add_argument(
            "--no-change",
            action="store_true",
            help="The scenario is expected not to mutate roles/channels",
        )
        sub.add_parser("cleanup")
        args = parser.parse_args(argv)
        subcommand = args.subcommand or "run"
        if subcommand == "snapshot":
            return await self.snapshot_command()
        if subcommand == "cleanup":
            return await self.cleanup_command()
        if subcommand == "manual":
            return await self.manual_command(args)
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

    async def manual_command(self, args: argparse.Namespace) -> int:
        command_contract = get_command(args.manager_command) if args.manager_command else None
        if command_contract and command_contract.destructive:
            if not self.settings.destructive_allowed or not args.destructive:
                print(
                    "Destructive manual scenario blocked: set E2E_ALLOW_DESTRUCTIVE=true "
                    "and pass --destructive."
                )
                return 2

        lock = RunLock(self.settings.fixture_manifest.parent / "run.lock")
        try:
            lock.acquire()
        except RunAlreadyActive as exc:
            print(f"Run blocked: {exc}")
            return 2

        try:
            async with self._client() as client:
                gate = ManualActorGate(
                    client,
                    timeout=self.settings.request_timeout,
                    interval=self.settings.poll_interval,
                )
                checkpoint = await gate.checkpoint(
                    args.instruction,
                    actor_id=args.actor_id,
                )
                if args.no_change:
                    await asyncio.sleep(self.settings.poll_interval)
                    after = await snapshot_guild(client)
                    diff = compare_snapshots(checkpoint.before, after)
                else:
                    after, diff = await gate.wait_for_change(
                        checkpoint,
                        description=f"a Discord state change for {args.scenario}",
                        require_diff=True,
                    )

                output_dir = self.settings.report_dir / "manual" / args.scenario
                output_dir.mkdir(parents=True, exist_ok=True)
                before_path = output_dir / "before.json"
                after_path = output_dir / "after.json"
                result_path = output_dir / "result.json"
                before_path.write_text(
                    json.dumps(snapshot_to_dict(checkpoint.before), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                after_path.write_text(
                    json.dumps(snapshot_to_dict(after), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                payload = {
                    "scenario_id": args.scenario,
                    "command": command_contract.name if command_contract else args.manager_command,
                    "command_destructive": command_contract.destructive if command_contract else False,
                    "instruction": args.instruction,
                    "actor_id": args.actor_id,
                    "expect_change": not args.no_change,
                    "before_snapshot": str(before_path),
                    "after_snapshot": str(after_path),
                    "diff": {
                        "created": diff.created,
                        "deleted": diff.deleted,
                        "modified": diff.modified,
                        "unchanged": diff.unchanged,
                        "unexpected": diff.unexpected,
                        "missing": diff.missing,
                    },
                    "audit_before": checkpoint.before_audit,
                    "captured_at_epoch": time.time(),
                    "note": "Observation artifact only; matrix-specific assertions and command-response review are required for PASS/FAIL.",
                }
                result_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                assert_guild_identity(after, self.settings.guild_id)
                print(f"Manual scenario evidence written to {output_dir}")
                print(json.dumps(payload["diff"], indent=2, ensure_ascii=False))
            return 0
        finally:
            lock.release()

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

    @staticmethod
    def _member_permission_bits(member: dict, roles_by_id: dict[int, dict]) -> int:
        permissions = 0
        for raw_role_id in member.get("roles", []):
            try:
                role_id = int(raw_role_id)
            except (TypeError, ValueError):
                continue
            role = roles_by_id.get(role_id)
            if role is not None:
                permissions |= int(role.get("permissions", 0))
        return permissions

    @staticmethod
    def _role_permission_details(member: dict, roles_by_id: dict[int, dict]) -> list[dict[str, object]]:
        details: list[dict[str, object]] = []
        for raw_role_id in member.get("roles", []):
            try:
                role_id = int(raw_role_id)
            except (TypeError, ValueError):
                continue
            role = roles_by_id.get(role_id)
            if role is None:
                details.append({"id": role_id, "missing_from_guild_roles": True})
                continue
            details.append(
                {
                    "id": role_id,
                    "name": role.get("name"),
                    "position": int(role.get("position", 0)),
                    "permissions": int(role.get("permissions", 0)),
                    "managed": bool(role.get("managed", False)),
                }
            )
        return details

    @staticmethod
    def _top_role_position(member: dict, roles_by_id: dict[int, dict]) -> int:
        positions = [
            int(roles_by_id[int(raw_role_id)].get("position", 0))
            for raw_role_id in member.get("roles", [])
            if int(raw_role_id) in roles_by_id
        ]
        return max(positions, default=0)

    async def _environment(self, client: DiscordClient) -> tuple[str, dict]:
        me = await client.current_user()
        guild = await client.guild()
        roles = await client.guild_roles()
        role_map = {int(role["id"]): role for role in roles}

        runner_member = await client.guild_member(int(me["id"]))
        runner_permissions = self._member_permission_bits(runner_member, role_map)
        runner_top_position = self._top_role_position(runner_member, role_map)

        details = {
            "runner_bot_id": int(me["id"]),
            "guild_id": int(guild["id"]),
            "guild_name": guild["name"],
            "runner_role_count": len(runner_member.get("roles", [])),
            "runner_top_role_position": runner_top_position,
            "runner_roles": self._role_permission_details(runner_member, role_map),
            "runner_permissions": {
                "manage_channels": has_permission(runner_permissions, MANAGE_CHANNELS),
                "manage_roles": has_permission(runner_permissions, MANAGE_ROLES),
                "view_audit_log": has_permission(runner_permissions, VIEW_AUDIT_LOG),
            },
        }

        missing_runner = [
            name
            for name, ok in details["runner_permissions"].items()
            if name in {"manage_channels", "manage_roles"} and not ok
        ]
        if missing_runner:
            raise RuntimeError(
                "E2E Observer bot is missing required guild permission(s): "
                + ", ".join(missing_runner)
                + ". Its role permissions as observed by Discord were: "
                + json.dumps(details["runner_roles"], ensure_ascii=False)
            )

        if not has_permission(runner_permissions, VIEW_AUDIT_LOG):
            details["audit_log_note"] = "Runner cannot collect audit-log evidence without View Audit Log."

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

            target_permissions = self._member_permission_bits(target, role_map)
            target_top_position = self._top_role_position(target, role_map)
            target_role_details = self._role_permission_details(target, role_map)
            target_permission_ok = {
                "manage_channels": has_permission(target_permissions, MANAGE_CHANNELS),
                "manage_roles": has_permission(target_permissions, MANAGE_ROLES),
            }
            if not all(target_permission_ok.values()):
                missing = [name for name, ok in target_permission_ok.items() if not ok]
                raise RuntimeError(
                    "Target School Manager bot is missing required guild permission(s): "
                    + ", ".join(missing)
                    + ". Observed target roles: "
                    + json.dumps(target_role_details, ensure_ascii=False)
                )

            details["target_bot_id"] = self.settings.target_bot_id
            details["target_bot_tag"] = user.get("username")
            details["target_bot_top_role_position"] = target_top_position
            details["target_bot_roles"] = target_role_details
            details["target_bot_permissions"] = {
                **target_permission_ok,
                "view_audit_log": has_permission(target_permissions, VIEW_AUDIT_LOG),
                "administrator": has_permission(target_permissions, 1 << 3),
            }

            # Position 1 is a usable bot role directly above @everyone. The
            # actual role hierarchy is enforced when the bot manages a target role.
            if target_top_position <= 0:
                raise RuntimeError(
                    "Target School Manager bot has no usable role hierarchy above @everyone."
                )

        snapshot = await snapshot_guild(client)
        assert_guild_identity(snapshot, self.settings.guild_id)
        return (
            "REST access and configured guild scope are valid; observer permissions, target-bot membership, "
            "permissions, and basic hierarchy are verified when configured.",
            details,
        )

    async def _baseline(self, client: DiscordClient) -> tuple[str, dict]:
        snapshot = await snapshot_guild(client)
        assert_unique_role_names(snapshot)
        return "Baseline snapshot captured; no command was invoked by the runner.", {
            "roles": len(snapshot.roles),
            "channels": len(snapshot.channels),
            "captured_at": snapshot.captured_at,
        }
