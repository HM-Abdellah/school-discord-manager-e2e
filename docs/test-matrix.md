# E2E test matrix

| Area | External observation | Invocation requirement | Destructive | Phase |
|---|---|---|---|---|
| Environment | guild identity, bot membership, roles/channels, permissions | none | no | A |
| Fresh build | expected categories/channels/roles | `/setup` + build actor | yes | B |
| Build idempotency | no duplicate managed resources | `/build` twice | no | B |
| Add stream | only target stream resources appear | `/addstream` actor | yes | B |
| Student assignment | roles + visible channel state | `/assignstudent` actor | no | C |
| Duplicate assignment | stable state / no duplicate enrollment | `/assignstudent` actor | no | C |
| Transfer/history/leave | roles + externally visible state | actor | no | C |
| Teacher workflows | role and subject-channel access changes | actor | no | C |
| Timetable/exams/absence | destination channel and resulting messages/state | actor + attachment where needed | no | D |
| Remove stream | only recorded target resources change | `/removestream` actor | yes | D |
| Reset scope | managed resources deleted, fixtures/custom resources retained | owner actor | yes | D |
| Permission boundaries | allowed/forbidden command behavior | multiple real actors | no | E |
| Recovery | deleted managed channel/role rebuilt without duplicates | actor | yes | E |
| Academic year | externally visible state plus later historical state | actor | no | E |
| Final consistency | Discord state matches expected configuration model | none/actor depending on previous test | no | F |

## Invocation model

The runner supports a human-in-the-loop live workflow:

1. The runner authenticates only as the dedicated E2E **bot account** using a bot token.
2. The operator performs the application command in Discord with a normal user account.
3. The runner captures a before snapshot, waits for the human action, captures the after snapshot, computes an ID-based diff, and stores evidence.
4. Matrix-specific assertions decide whether the observed transition is a scenario pass or failure.

The runner never logs in as a normal user, never accepts a user token, and never fabricates Discord interaction payloads.

## Current implementation

The `python -m e2e run` command performs environment sanity checks and an observation baseline. The `python -m e2e manual` command executes the human-in-the-loop observation workflow for one scenario.

Example:

```bash
python -m e2e manual \
  --scenario CORE-001 \
  --actor-id 123456789012345678 \
  --instruction "Use the normal Discord client to open /setup, select the configured test levels/streams, confirm the summary, and complete the build."
```

For scenarios where roles/channels are not expected to change, add `--no-change`:

```bash
python -m e2e manual \
  --scenario CORE-005 \
  --actor-id 123456789012345678 \
  --no-change \
  --instruction "Use the normal Discord client to run /status and verify the response."
```

Evidence is written below `reports/manual/<scenario-id>/` and includes the before/after snapshots plus a JSON result containing the observed diff and optional audit-log evidence.

This workflow is intentionally not a fully unattended Discord command driver. Discord's supported bot API does not provide a documented way for one bot to execute another application's slash command as an arbitrary human user, and self-bot/user-token automation is out of scope.
