# E2E architecture

## Scope

The runner is an external observer/orchestrator for one isolated Discord guild. It does not import School Manager internals and does not share its SQLite database or guild configuration file.

```text
                         Discord
                            ^
                            |
                   School Manager bot
                            |
             +--------------+--------------+
             |                             |
        Discord state                 persistent state
             ^
             |
       E2E REST observer
             |
   snapshots / waits / evidence
             |
       runner + assertions
```

## Components

### `discord_client.py`
Single-guild REST boundary. Every guild-scoped request validates the configured guild ID. Mutating requests pass through the pacing layer.

### `pacing.py`
Conservative mutation serialization. A mutation waits for the configured minimum gap; batches are followed by a cooldown; rate-limit responses are respected; repeated rate limiting stops the run. The jitter is only for smoothing request bursts, not for disguising automation.

### `snapshots.py`
Captures externally observable roles and channels, including parent relationships, positions and permission overwrites. Snapshot comparisons classify created, deleted, modified and unchanged resources by stable Discord ID.

### `fixtures.py`
Tracks resources created by the runner using exact Discord IDs. Cleanup deletes only registered IDs and retains failed cleanup entries for a later retry.

### `waiting.py`
Polling primitives for eventual consistency. Tests wait for an observed state rather than sleeping a fixed amount after every operation.

### `actors.py`
Stores actor metadata only. Credentials and user-token automation do not belong here.

### `reporting.py`
Produces console, JSON and HTML test records. Future evidence bundles can include snapshots and audit-log observations.

## Resource safety model

The runner uses two identities for reasoning:

1. **Runner-owned:** exact fixture IDs created by this process.
2. **Observed managed resources:** resources that School Manager exposes in Discord and that tests identify by expected structure plus state transitions.

The runner never decides ownership from a name alone when an exact ID is available.

## Destructive operations

No destructive suite is enabled by default. A destructive run requires configuration permission and an explicit CLI flag. A future destructive test should capture at least:

```text
pre-operation snapshot
pre-operation evidence
operation result / actor evidence
post-operation snapshot
snapshot diff
cleanup result
```

## Synchronization

The preferred pattern is:

```python
before = await snapshot_guild(client)
# actor performs operation through a supported invocation path
await wait_until(expected_state, ...)
after = await snapshot_guild(client)
diff = compare_snapshots(before, after)
assert_diff(diff, expectation)
```

Fixed sleeps remain available only for rare externally imposed cooldowns; they are not the normal synchronization primitive.
