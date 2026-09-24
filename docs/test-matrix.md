# E2E test matrix

The canonical synchronized matrix files are stored in `matrix/` in this repository.

Source application commit:

```text
school-discord-manager main
0f14d5f31474b3008ea2e698d52358065eda9111
```

## Current coverage

| Matrix | Cases | Scope |
|---|---:|---|
| `core_commands.json` | 20 | Core commands and destructive boundaries |
| `permission_roles.json` | 7 | OWNER / MEMBER / MEMBER_ADMIN and role hierarchy |
| `sections_timetable_exam.json` | 18 | Sections 1..8, timetable, exams, attachment/channel boundaries |
| `failure_recovery.json` | 19 | Fail-closed, recovery, persistence and pending-removal boundaries |
| `concurrency_regression.json` | 16 | Mutation serialization, concurrent assignments and regression |
| **Total** | **80** | |

## Current command surface

The E2E command catalog is synchronized with the current School Manager command surface, including:

- `/status`
- `/serverhealth`
- `/adminpanel`
- `/create-section-threads`

The section-thread command is specifically covered by live verification of active + archived public-thread idempotency. Its matrix-level behavior must not be replaced by a channel-count-only assertion.

## Invocation model

The observer bot never invokes School Manager slash commands.

1. A normal Discord user performs the command.
2. The observer captures the before state.
3. The operator performs the action in the Discord client.
4. The observer captures the after state.
5. The operator evaluates command-response semantics and matrix expectations.
6. Evidence is retained under `reports/manual/<scenario-id>/`.

## Snapshot boundary

Snapshots are authoritative for structural Discord state visible through the observer:

- guild identity;
- roles;
- channels;
- channel parent relationships;
- permission overwrites;
- stable Discord IDs.

They are **not** a complete message-history/thread-content oracle. Message/thread scenarios require explicit client-side verification.

## Fault-injection boundary

The failure matrix intentionally contains cases that cannot be proven through a normal happy-path Discord run. A scenario requiring SQLite corruption, persistence failure, or an injected Discord API failure needs a controlled test harness or code-level fault injection.

Never mark those cases as live PASS without actually injecting the stated fault.

## Completion rule

A scenario is PASS only when both:

1. the human actor observed the expected command/interaction semantics;
2. the captured Discord evidence matches the scenario contract.

The runner's exit code is an infrastructure result, not a matrix verdict.
