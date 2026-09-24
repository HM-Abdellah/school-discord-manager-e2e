# Live Discord E2E operator runbook

This runbook is synchronized with School Discord Manager main commit `0f14d5f31474b3008ea2e698d52358065eda9111`.

## 1. Required processes

You need:

1. **School Discord Manager** running from its own repository.
2. **school-discord-manager-e2e** running from its own repository.
3. One normal Discord user account (OWNER).
4. A second normal Discord user account when AUTH/CONCURRENCY scenarios require MEMBER_ADMIN or MEMBER.
5. A dedicated E2E Discord guild.

The observer is the bot named `school-discord-manager-e2e`. Its local repository/folder is separate from the School Manager repository.

## 2. E2E environment

From:

```text
C:\Users\user\Desktop\school-discord-manager-e2e
```

activate its own virtual environment:

```powershell
cd C:\Users\user\Desktop\school-discord-manager-e2e
.venv\Scripts\Activate.ps1
```

Create `.env.e2e` from `.env.example` and set:

```text
DISCORD_TOKEN=<observer bot token>
DISCORD_GUILD_ID=<dedicated E2E guild ID>
TARGET_BOT_ID=<School Manager bot user ID>
```

Do **not** use the old variable names `E2E_BOT_TOKEN` or `E2E_GUILD_ID` with this repository.

## 3. Start the School Manager

In its separate terminal/repository:

```powershell
cd C:\Users\user\Desktop\school-discord-manager
.venv\Scripts\Activate.ps1
python bot.py
```

Confirm the School Manager starts without errors.

## 4. Preflight the observer

In the E2E repository terminal:

```powershell
python -m e2e run
```

Expected result:

- environment sanity passes;
- target bot is found in the configured guild;
- required permissions/hierarchy are present;
- baseline snapshot is captured.

**Do not run `/resetserver` before this gate passes.**

## 5. Scenario execution

Choose the exact scenario ID from `matrix/`.

Example:

```powershell
python -m e2e manual \
  --scenario CORE-001 \
  --actor-id 123456789012345678 \
  --instruction "Run /setup in Discord, configure the selected test streams, confirm, and complete the build."
```

The runner waits for the normal user to perform the action. It does not execute the slash command itself.

For read-only scenarios:

```powershell
python -m e2e manual \
  --scenario CORE-005 \
  --actor-id 123456789012345678 \
  --no-change \
  --instruction "Run /status in Discord and verify the response."
```

## 6. Destructive scenarios

Set:

```text
E2E_ALLOW_DESTRUCTIVE=true
```

and pass `--destructive`.

Before `/resetserver`, capture the baseline and verify the dedicated guild contains the intended managed state plus any explicit unmanaged comparison fixtures.

Never use destructive commands against a production guild.

## 7. Evidence

Each manual scenario produces:

```text
reports/manual/<scenario-id>/
├── before.json
├── after.json
└── result.json
```

Review all of:

1. command response/interaction in Discord;
2. before/after snapshot;
3. ID-based diff;
4. audit-log evidence when available;
5. the exact expectation in the matching matrix case.

The runner does not automatically declare a scenario PASS merely because a Discord resource changed.

## 8. Threads and messages

The observer snapshot is intentionally structural: roles, channels, parent relationships, and permission overwrites.

For message/thread scenarios such as:

- `/create-section-threads`;
- `/set_timetable`;
- `/setexam`;
- `/reportabsence`;

the operator must also verify the actual Discord message/thread result in the client. Do not infer message correctness from a channel snapshot alone.

## 9. Failure/recovery boundary

The failure matrix contains both live-testable cases and cases that require controlled fault injection.

Do not claim PASS for a fault-injection case by merely executing the happy path. Record such cases separately as:

- live verified;
- fault-injection verified;
- not executed.

## 10. Cleanup

After a scenario or suite:

```powershell
python -m e2e cleanup
```

Cleanup is ID-scoped to the configured guild. If cleanup fails, keep the manifest and investigate the exact failed fixture instead of deleting by name.

## 11. Completion

Phase completion requires:

- synchronized matrix reviewed;
- E2E preflight green;
- required live scenarios executed in the dedicated guild;
- command responses reviewed;
- Discord evidence reviewed;
- fault-injection cases explicitly distinguished from live cases;
- final cleanup and final guild-state verification completed.
