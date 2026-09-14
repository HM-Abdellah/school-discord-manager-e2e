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

## Current implementation rule

Only Phase-A observation is executable automatically by the runner. Command-driven rows remain explicit contracts until a supported actor-invocation path is selected.

This prevents the test framework from silently turning into a self-bot or into an undocumented Discord-client emulator.
