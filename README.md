# School Discord Manager — E2E Test Runner

Independent Python E2E runner for an isolated Discord guild used to validate the real external behavior of School Discord Manager.

## Current state

Phase A is implemented. The runner can observe Discord state, capture snapshots, compare state transitions, create and clean up its own fixtures, wait for eventual consistency, collect optional audit-log evidence, serialize mutations, and stop safely under repeated rate limiting.

The runner deliberately does **not** automate a normal Discord user account and does not fabricate slash-command interactions. Discord's documented APIs provide bot accounts for automation, while self-bots/user-bots are prohibited.

## Why commands are not invoked yet

School Discord Manager exposes its functionality as application commands. `/setup` is also an interactive select/button workflow. A separate bot-token REST client cannot legitimately press `/build` or `/assignstudent` as an arbitrary human user.

Therefore the project separates:

```text
Observation       -> fully automated now
Actor invocation  -> requires a supported actor path
System behavior   -> observed from real Discord state
```

See `docs/interaction-model.md` for the decision and the safe options for a future fully unattended mode.

## Safety model

- One configured guild only (`DISCORD_GUILD_ID`).
- No hardcoded secrets or server IDs.
- Destructive suites require both `E2E_ALLOW_DESTRUCTIVE=true` and `--destructive`.
- Guild mutations are serialized and paced conservatively.
- Discord `Retry-After` is honored.
- Repeated rate limiting stops the run instead of trying to stay just below a threshold.
- Fixture cleanup uses exact resource IDs and refuses to delete channel fixtures that are not currently in the configured guild.
- Failed cleanup entries remain in `.e2e/fixtures.json` for a later retry.
- A cross-process run lock prevents two E2E runs from mutating the same test guild concurrently.

The pacing system is intended to reduce burst load and let Discord state settle. It is not a mechanism for disguising automation or bypassing anti-spam systems.

## Evidence

When the runner has `VIEW_AUDIT_LOG`, `e2e.evidence.capture_audit_evidence()` can capture recent administrative actions through Discord's documented audit-log endpoint. Audit-log entries include the actor, action type, target, and optional reason fields; this provides useful supporting evidence for resource changes.

Snapshots record roles and channels by stable Discord ID, including parent relationships and permission overwrites. Diffs classify created, deleted, modified, and unchanged resources.

## Layout

```text
school-discord-manager-e2e/
├── e2e/
│   ├── __main__.py
│   ├── runner.py
│   ├── config.py
│   ├── discord_client.py
│   ├── pacing.py
│   ├── waiting.py
│   ├── models.py
│   ├── snapshots.py
│   ├── assertions.py
│   ├── fixtures.py
│   ├── cleanup.py
│   ├── run_lock.py
│   ├── actors.py
│   ├── evidence.py
│   ├── reporting.py
│   └── tests/
├── docs/
│   ├── architecture.md
│   ├── interaction-model.md
│   └── test-matrix.md
├── reports/
├── .e2e/
├── .env.example
├── .gitignore
├── requirements.txt
└── pyproject.toml
```

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env.e2e
```

Put only the isolated test guild ID, runner bot token, and optional target bot ID in `.env.e2e`. Never commit it.

## Phase A commands

```bash
python -m e2e snapshot
python -m e2e run
python -m e2e cleanup
```

`run` currently performs environment sanity and an observation baseline only. It intentionally does not pretend to invoke School Manager slash commands.

## Next implementation phase

The next phase will add the first real command-driven workflow only after the actor-invocation path is explicitly selected. The first candidate is the smallest useful workflow around `/setup` and `/build`, followed by an idempotency check based on before/after snapshots rather than a fixed sequence of blind sleeps.
