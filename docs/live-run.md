# Live Discord E2E operator runbook

This runbook describes how to execute a live scenario against an isolated Discord test guild without using self-bots, user tokens, or undocumented Discord endpoints.

## 1. Test environment

Use a dedicated Discord test guild. Do not point this runner at a production school guild.

You need:

- the School Discord Manager bot installed in the test guild;
- the E2E observer bot installed in the same test guild;
- one normal Discord user account to perform application commands;
- a second normal Discord user account when the matrix requires a different permission role or owner/management boundary.

The observer bot should receive only the permissions needed for the configured observation and fixture duties. `View Audit Log` is optional; without it the run continues without audit-log evidence.

## 2. Local configuration

Copy the template:

```powershell
copy .env.example .env.e2e
```

Set:

```text
DISCORD_TOKEN=<E2E observer bot token>
DISCORD_GUILD_ID=<dedicated test guild ID>
TARGET_BOT_ID=<School Discord Manager bot user ID>
```

Credentials must stay in `.env.e2e`; this file is ignored by Git and must never be committed.

## 3. Validate the observer before changing the guild

```bash
python -m e2e run
```

The runner validates its own bot membership and permissions, validates the target bot when `TARGET_BOT_ID` is configured, checks the guild identity, and captures an observation baseline.

Do not continue when environment sanity fails.

## 4. Run one scenario

Use the exact stable scenario ID from the School Discord Manager matrix.

```powershell
python -m e2e manual `
  --scenario CORE-001 `
  --actor-id 123456789012345678 `
  --instruction "Use the normal Discord client to open /setup, select the configured test levels/streams, confirm the summary, and complete the build."
```

The runner captures the before state and pauses. The operator then performs the action in Discord using the normal Discord client. When finished, press Enter in the runner terminal.

For scenarios expected not to mutate roles/channels, use `--no-change`:

```powershell
python -m e2e manual `
  --scenario CORE-005 `
  --actor-id 123456789012345678 `
  --no-change `
  --instruction "Use the normal Discord client to run /status and verify the response."
```

## 5. Review evidence

Each run is stored under:

```text
reports/manual/<scenario-id>/
├── before.json
├── after.json
└── result.json
```

`result.json` contains the observed Discord diff and the optional audit-log snapshot. A resource appearing in `created`, `deleted`, or `modified` is evidence of an external state transition; it is not by itself a pass/fail verdict.

## 6. Scenario verdict

Compare the evidence with the scenario contract in the School Discord Manager repository.

Record a scenario as `PASS` only when both are satisfied:

1. the human actor observed the expected command response/interaction semantics;
2. the before/after Discord evidence matches the scenario's expected external state.

A `PASS` must not be inferred solely from the process exit code of the runner.

Record a `FAIL` when the command behavior, Discord state, authorization boundary, or resource ownership differs from the matrix expectation.

## 7. Destructive scenarios

For destructive scenarios, set:

```text
E2E_ALLOW_DESTRUCTIVE=true
```

and use the runner's `--destructive` guard where applicable. Keep destructive tests confined to the isolated test guild.

Before a destructive scenario, make sure any runner-owned fixture or intentionally unmanaged comparison resource is present exactly as the scenario requires. After the scenario, use the runner cleanup command and review the cleanup manifest.

## 8. Cleanup

```bash
python -m e2e cleanup
```

Cleanup is ID-based and stays within the configured guild. If cleanup fails, keep the manifest and investigate before retrying; do not broaden deletion by name.

## 9. Phase 3 completion record

Keep the evidence for the executed live scenarios and record:

- scenario ID;
- actor account used;
- date/time of run;
- command response observation;
- before/after snapshot paths;
- result diff;
- PASS/FAIL verdict and reason.

Phase 3 is complete only when the required live scenarios have been executed against the dedicated test guild and the evidence has been reviewed.
