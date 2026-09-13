# School Discord Manager — E2E Test Runner

Independent Python E2E runner for an isolated Discord guild used to validate the real external behavior of School Discord Manager.

## Phase A

The first milestone contains only:

- documented Discord REST observation
- strict single-guild scope
- guild snapshots and state diffs
- runner-owned fixtures
- exact-ID cleanup
- state synchronization helpers
- JSON/HTML/console reporting
- conservative mutation pacing and rate-limit safety

Slash-command invocation is intentionally **not** implemented yet. The runner will not use self-bots, user tokens, fabricated interaction payloads, or undocumented endpoints to impersonate a human invoking a command.

## Discord safety model

The runner uses a normal Discord bot token against the documented API. Guild mutations are serialized, paced conservatively, and stopped after repeated rate-limit responses. The pacing layer exists to reduce burst load and allow Discord state to settle; it is not an anti-spam bypass or a method for disguising automation.

See Discord's current policies and API documentation before enabling destructive suites:

- https://discord.com/guidelines
- https://discord.com/safety/platform-manipulation-policy-explainer
- https://docs.discord.com/developers/topics/rate-limits

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
│   ├── actors.py
│   ├── reporting.py
│   └── tests/
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

Put only the isolated test guild ID and bot token in `.env.e2e`. Never commit it.

## Phase A commands

```bash
python -m e2e snapshot
python -m e2e run
python -m e2e cleanup
```

`run` currently performs environment sanity + an observation baseline only. Real command-driven suites are held back until the supported interaction model is settled.

## Safety gates

Destructive test runs require both:

```text
E2E_ALLOW_DESTRUCTIVE=true
```

and:

```bash
python -m e2e run --destructive
```

The runner refuses to address a guild other than `DISCORD_GUILD_ID`. Fixture cleanup only touches exact resource IDs recorded by the runner.
