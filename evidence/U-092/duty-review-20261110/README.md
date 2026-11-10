# U-092 review: closed service still starts model dispatch

2026-11-10. Independent reviewer: the single codex-home duty session.
Implementation remains with the original #46 owner and developer session
`01a1c217`. This is a negative review of an unpublished source snapshot, not
approval of a commit or implementation of the author's recovery feature.

**P1: service closure is checked at entry and after the model returns, but
not at dispatch admission.** In `WorkService._run_step`, channel construction
and the final material-binding check can finish after `ConsoleApp.close()`
has released the directory guard. The old service still calls `transport.chat`.
In the channel-construction case it also commits a new reservation after
closing. A late rejection prevents result adoption, but cannot undo that call.

The [contract](contract.md) was frozen before running the new
[executable probes](probes.py). The product source was not modified:

| Scenario | Expected fake dispatches | Observed | Durable state |
| --- | ---: | ---: | --- |
| Live service control | 1 | 1 | Original step used |
| Close during channel construction | 0 | 1 | New original reservation committed after close |
| Close after reservation, before transport | 0 | 1 | Original reservation retained |

All three cases use real temporary Console/HTTP/SQLite fixtures and an
explicit fake model. There are two assertion failures, zero runtime errors.
The author's existing 19 recovery tests pass independently on this snapshot.
No real inference, production restart, migration or author-file/index write
occurred. Full Python/npm/Chrome validation was not repeated for this rejected
prepublication review; those remain implementation/publication gates.

The copy is based on integration `63c4030ec1c520824c00633e42b45019a3e9c533`.
[Validation](validation.json) records all 20 changed/new file hashes, the
snapshot manifest hash, individual observations and private-log hashes.
The author's files still matched all 20 hashes after probing. This is stronger
than an unbound working-directory result, but does not replace an exact PR
head and CI. No author source is imported by this review branch.

Run with the pinned Python against an isolated copy containing the author's
`tests/test_work_recovery.py` and recovery implementation:

```text
python -B evidence/U-092/duty-review-20261110/probes.py <candidate-source-directory> <private-result.json>
```

Exit 1 currently reproduces both failures. The next implementation needs
shutdown and dispatch admission to agree on current execution ownership before
any transport call, including closure during channel preparation. Preserve the
already committed reservation and original IDs; do not turn shutdown into
proof of remote non-execution. Keep the live-service control, add the two
boundaries to normal regression coverage, and publish the exact candidate for
follow-up independent review. #46 owner/progress/WIP, #47/#52 dependencies and
the real parent acceptance remain unchanged.
