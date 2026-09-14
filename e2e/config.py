from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .pacing import PacingConfig


def _optional_snowflake(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    if not raw.isdigit():
        raise RuntimeError(f"{name} must be a numeric Discord ID when provided.")
    return int(raw)


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    guild_id: int
    target_bot_id: int | None
    destructive_allowed: bool
    request_timeout: float
    poll_interval: float
    max_retries: int
    report_dir: Path
    fixture_manifest: Path
    pacing: PacingConfig

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv(".env.e2e")
        load_dotenv(".env")
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required.")

        raw_guild = os.getenv("DISCORD_GUILD_ID", "").strip()
        if not raw_guild.isdigit():
            raise RuntimeError("DISCORD_GUILD_ID must be a numeric Discord guild ID.")

        return cls(
            discord_token=token,
            guild_id=int(raw_guild),
            target_bot_id=_optional_snowflake("TARGET_BOT_ID"),
            destructive_allowed=os.getenv("E2E_ALLOW_DESTRUCTIVE", "false").strip().lower() == "true",
            request_timeout=float(os.getenv("E2E_TIMEOUT", "20")),
            poll_interval=float(os.getenv("E2E_POLL_INTERVAL", "0.75")),
            max_retries=int(os.getenv("E2E_MAX_RETRIES", "5")),
            report_dir=Path(os.getenv("E2E_REPORT_DIR", "reports")),
            fixture_manifest=Path(os.getenv("E2E_FIXTURE_MANIFEST", ".e2e/fixtures.json")),
            pacing=PacingConfig(
                min_mutation_delay=float(os.getenv("E2E_MIN_MUTATION_DELAY", "2.0")),
                max_jitter=float(os.getenv("E2E_MAX_MUTATION_JITTER", "2.5")),
                max_consecutive_mutations=int(os.getenv("E2E_MAX_CONSECUTIVE_MUTATIONS", "5")),
                cooldown_after_batch=float(os.getenv("E2E_BATCH_COOLDOWN", "5.0")),
                max_rate_limit_events=int(os.getenv("E2E_MAX_RATE_LIMIT_EVENTS", "3")),
            ),
        )
