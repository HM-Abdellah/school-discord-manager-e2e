# School Discord Manager — E2E Observer

Independent Python E2E observer for validating the real Discord behavior of **School Discord Manager** in a dedicated test guild.

## Compatibility

This repository is synchronized with School Discord Manager:

- Target branch: `main`
- Target commit: `0f14d5f31474b3008ea2e698d52358065eda9111`
- E2E harness version: `0.2.0`

The synchronized matrix is stored locally under `matrix/` so the live run does not depend on a second checkout of the application repository.

## Execution model

```text
Normal Discord user
       |
       | executes slash commands in Discord
       v
School Discord Manager
       |
       | real Discord mutations
       v
Dedicated E2E guild
       ^
       |
Dedicated E2E observer bot
       |
       +-- environment gate
       +-- snapshots / ID-based diffs
       +-- audit-log evidence (optional)
       +-- fixture cleanup
       +-- pacing / retries
       +-- cross-process run lock
       +-- manual scenario evidence
```

The observer never logs in as a normal user, never accepts a user token, and never fabricates slash-command interactions.

## Setup

From the `school-discord-manager-e2e` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env.e2e
```

Configure only the isolated test environment:

```text
DISCORD_TOKEN=<school-discord-manager-e2e observer bot token>
DISCORD_GUILD_ID=<dedicated E2E guild ID>
TARGET_BOT_ID=<school-discord-manager bot user ID>
```

Optional settings are documented in `e2e/config.py`. Never commit `.env.e2e`.

## Preflight

Run this **before any destructive Discord operation**:

```powershell
python -m e2e run
```

It verifies:

- observer bot membership and required permissions;
- target School Discord Manager bot membership when configured;
- target bot role hierarchy and required permissions;
- guild identity;
- unique role names;
- a REST observation baseline.

A successful preflight does not execute a School Manager slash command.

## Live scenario

Use the exact ID from `matrix/*.json`:

```powershell
python -m e2e manual \
  --scenario CORE-001 \
  --actor-id 123456789012345678 \
  --instruction "Use the normal Discord client to run the scenario exactly as described in matrix/core_commands.json."
```

For read-only/no-role-channel-change scenarios:

```powershell
python -m e2e manual \
  --scenario CORE-005 \
  --actor-id 123456789012345678 \
  --no-change \
  --instruction "Use the normal Discord client to run /status and verify the response."
```

The runner captures the before state, waits for the human action, captures the after state, and writes:

```text
reports/manual/<scenario-id>/
├── before.json
├── after.json
└── result.json
```

The diff is evidence, not an automatic PASS/FAIL verdict. The operator must also verify the visible command response and matrix-specific expectations.

## Destructive safety

Destructive manual scenarios require both:

```text
E2E_ALLOW_DESTRUCTIVE=true
```

and:

```powershell
--destructive
```

This applies to commands such as `/resetserver`, `/removestream`, and `/rollbackyear`. Keep them inside the dedicated E2E guild.

## Cleanup

```powershell
python -m e2e cleanup
```

Cleanup is ID-based and refuses to broaden deletion by resource name.

## Matrix

The current synchronized matrix contains:

- 20 core command scenarios;
- 7 authorization/role scenarios;
- 18 section/timetable/exam scenarios;
- 19 failure/recovery scenarios;
- 16 concurrency/regression scenarios.

Total: **80 scenarios**.

Some failure cases require controlled fault injection and must not be falsely marked as live-tested merely because the normal Discord workflow passed. The matrix itself defines the expected test boundary.

## Important boundary

`python -m e2e run` is an **environment gate + observation baseline**, not an unattended execution of all 80 scenarios.

The real slash commands are executed by a normal Discord user. This keeps the test inside Discord's supported interaction model and avoids self-bot/user-token automation.
