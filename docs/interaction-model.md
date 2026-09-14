# Discord interaction model

## Finding

School Discord Manager exposes its user-facing operations as Discord application commands. Its main entry point loads cogs and synchronizes the application command tree to the configured development guild. `/setup` is additionally an interactive component flow made of selects and buttons.

The external E2E runner uses a normal Discord bot token for observation and narrowly scoped fixtures. Discord does not provide a documented REST endpoint that lets one bot token execute another application's slash command as an arbitrary guild user.

The runner therefore must not:

- automate a normal user account (self-bot/user-bot);
- use a user token as an actor;
- forge or inject undocumented interaction payloads;
- call undocumented Discord client endpoints to simulate a human;
- treat rate-limit thresholds as something to evade.

Discord's current policy explicitly prohibits self-bots/user-bots and platform abuse, including automated spammy interactions. Bot API clients are the supported automation account type.

## Consequence for this project

There are three distinct layers:

```text
A. Observation
   E2E runner -> documented Discord REST API

B. Actor invocation
   Human/real Discord user -> Discord client -> School Manager interaction

C. System behavior
   School Manager -> Discord resources + persistent state
   E2E runner -> observes the resulting external state
```

Layer A can be fully automated now. Layer B cannot be reproduced by a separate bot through a documented Discord REST call. Therefore the first command-driven tests will use an explicit actor bridge rather than pretending that the REST client can invoke `/build`, `/assignstudent`, etc.

## Candidate full-automation path

If fully unattended command invocation is required later, the safe architectural option is a test-only invocation boundary in the School Manager application itself, enabled only for the isolated E2E environment. That boundary should call the same application/service layer used by the real Discord command handlers, while keeping authorization and validation explicit. It must not impersonate a user on Discord.

This decision is deferred until the external E2E observation and fixture layers are proven.
