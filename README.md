# School Discord Manager — E2E Test Runner

Independent Python E2E runner for an isolated Discord guild used to validate the real external behavior of School Discord Manager.

## Current state

The runner provides a ToS-safe observation and human-in-the-loop live E2E workflow. It can observe Discord state, capture snapshots, compare state transitions, create and clean up its own fixtures, wait for eventual consistency, collect optional audit-log evidence, serialize mutations, and stop safely under repeated rate limiting.

Command execution is intentionally performed by a **real normal Discord user account** in the Discord client. The runner itself authenticates only as a dedicated bot account for observation and fixture management; it never accepts or stores a user token and never fabricates slash-command interactions.

## Design

```text
Real Discord user
      |
      | performs /setup, /build, /addstream, ...
      v
Discord client
      |
      v
School Discord Manager
      |
      | real Discord resource changes
      v
Dedicated E2E guild
      ^
      |
E2E runner bot account
      |
      +-- snapshots / diffs
      +-- fixture isolation + cleanup
      +-- optional audit evidence
      +-- pacing / retries / run lock
      +-- manual scenario evidence
```

This avoids self-bot behavior while still testing the real Discord surface.

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
- Credentials belong only in the local `.env.e2e` file and must never be committed.

The pacing system is intended to reduce accidental burst load and let Discord state settle. It is not a mechanism for disguising automation or bypassing anti-spam systems.

## Evidence

When the runner has `VIEW_AUDIT_LOG`, `e2e.evidence.capture_audit_evidence()` can capture recent administrative actions through Discord's documented audit-log endpoint. Audit-log entries include the actor, action type, target, and optional reason fields; this provides supporting evidence for resource changes.

Snapshots record roles and channels by stable Discord ID, including parent relationships and permission overwrites. Diffs classify created, deleted, modified, and unchanged resources.

## Layout

```text
school-discord-manager-e2e/
├── e2e/
│   ├── __main__.py
│   ├── runner.py
│   ├── actor_gate.py
│   ├── actors.py
│   ├── command_catalog.py
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
│   ├── evidence.py
│   └── reporting.py
├── docs/
│   ├── architecture.md
│   ├── interaction-model.md
│   ├── test-matrix.md
│   └── live-run.md
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

## Commands

Environment observation:

```bash
python -m e2e snapshot
python -m e2e run
```

Manual live scenario:

```bash
python -m e2e manual \
  --scenario CORE-001 \
  --actor-id 123456789012345678 \
  --instruction "Use the normal Discord client to open /setup, select the configured test levels/streams, confirm the summary, and complete the build."
```

For a read-only scenario such as `/status` where the roles/channels should not change, use `--no-change`:

```bash
python -m e2e manual \
  --scenario CORE-005 \
  --actor-id 123456789012345678 \
  --no-change \
  --instruction "Use the normal Discord client to run /status and verify the response."
```

The manual command captures a before snapshot, waits for the operator to complete the action, captures the after state, computes an ID-based diff, and writes evidence under `reports/manual/<scenario-id>/`.

## Live E2E completion rule

A scenario is **not** automatically marked as passed just because Discord changed. The operator and test owner must compare the evidence against the corresponding scenario contract in the School Discord Manager E2E matrix and record the matrix-specific result.

For Phase 3 completion, the live scenarios must be executed against a dedicated test guild and the results retained as evidence. The runner's role is to make the Discord observation deterministic and safe; it does not impersonate a human actor.

## Discord platform boundary

The project intentionally does not:

- automate a normal Discord user account;
- use a user token as an actor;
- forge or inject undocumented interaction payloads;
- call undocumented Discord client endpoints to simulate a human;
- use rate-limit thresholds as something to evade.

If a future unattended mode is needed, use an explicit test-only application/service boundary inside School Discord Manager rather than impersonating a user account on Discord.
