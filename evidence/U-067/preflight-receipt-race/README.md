# Concurrent preflight refusal must preserve the original dispatch

2026-11-08. Implementer: codex-home, online member
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`. Scope and 1–2 hour estimate were
recorded in Kanban #22 comment #70; the original owner and incomplete real
acceptance stay unchanged. Branch: `codex/u067-preflight-receipt-race`.

Base: PR #28 at `894f5106a105a9ab269ef9035c9a40f36e5d791c`, including the
adopted PR #17/#26/#27 history and pending PR #24/#25/fixture changes. Its
14 successful checks do not certify this new change or replace independent
review. The original PR #22 drivers and 099/100 are outside this repair.

## Reproduced failure and minimal fix

Two identical commands can both finish their initial read before the first
reservation. One invocation may then fail to build its channel after the other
has already committed its reservation and entered the transport. Previously
that late preflight failure saved a terminal `rejected/effect=none` receipt.
The actual dispatch then returned that receipt instead of saving its completed
usage or unknown outcome. This is a distinct concurrency case from reentry
that starts after a reservation already exists.

The [contract](../../../specs/053-union-rewrite/s03-preflight-receipt-contract.md)
was written before the tests and implementation. The original code produced
**four failures and two passes** in six deterministic concurrency/control cases;
[the RED log](red.txt) retains them. No working code was removed.

`WorkService.store_receipt` now checks the original committed intent in the
same GovernanceStore transaction as the prospective refusal. An existing
immutable receipt still wins; a pending intent returns its original step and
model request without saving a terminal refusal. The invocation that owns the
dispatch can finish accounting. Six added lines, including comments, change
this boundary. No schema, audit-adoption rule or separate writer changes.

## Verification

The [behavior tests](../../../tests/test_work_preflight_race.py) use real local
SQLite and deterministic thread events with fake model calls. They cover:

- completed usage survives duplicate channel refusal, construction error, or
  an unavailable channel, with exactly one transport invocation;
- no terminal receipt is committed by the duplicate before the owner returns;
- an unknown response preserves its original reservation through restart and
  replay performs no additional dispatch;
- a completed original receipt wins over a later preparation failure;
- ordinary preparation refusal adds no reservation or AU version.

All **46** affected dispatch, parent-loop, compatibility and new race tests pass
([GREEN](green.txt)); all three original independent S03 probes pass. These
reruns verify this new implementation and are not a new independent review.
Full-suite and npm results are recorded in [verification.json](verification.json).
Python: **731 tests, eight skipped, passed** (456.365 seconds). `npm run check`
passes with 220 frontend, 37 management and nine action tests, typecheck and
build. The unchanged bundle-size warning remains. After recording delivery
history, management render and the 37 management checks also pass.
Raw full-suite logs remain host-local; only sanitized dedicated test logs and
hashes/summaries are published.

## Adoption boundary

This is a controlled engineering candidate. A different engineering role must
review this receipt/accounting change along with the pending PR #28 inputs;
all checks must pass on the candidate's current head before adoption. The
implementation session does not provide that independent approval. Preserve
the original PR heads/history when integrating, then check the combined head.

There were zero real model calls, NAS service switches or live-data migrations.
The existing vendor edit was preserved and excluded. No supervisor, host
configuration, scheduled task, agent lock/state or branch protection changed.
