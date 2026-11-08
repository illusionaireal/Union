# Overdue acceptance-driver correction

2026-11-08. Implementer: Codex foreground coordinator resuming session
`01a1b7fe-81cb-7ec0-8459-d85fd97a9ba7`; online member `codex-home`,
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`. The user expressly required intervention
when tasks remain blocked. Kanban #22 comment 76 / team message 42 records this
bounded takeover of the driver corrections; DSH retains the parent responsibility.

Author baseline: `0821cff9f0744ab90e55d9178bacca0c0495b378`. The new
[contract](../../../specs/053-union-rewrite/s03-acceptance-intervention-contract.md)
preceded behavior changes. Original driver code produced **14 assertion failures
across eight tests**; the valid complete fixture still passed. No working product
code was removed. The initial [RED](red.txt) is retained with host paths redacted.

The driver now verifies the explicit Go account, two distinct used request IDs,
each output limit and usage sum, exact document text/hash/bytes and paired tool
ID in the second model call, then downloads the candidate and checks its digest,
source receipt and unpredictable document token. A shaped summary is insufficient.
The bounded and interruption opt-ins are separate; their maxima are two and one
calls, and selecting both can consume three. Neither opt-in grants authorization.

The interruption driver matches AU/Work/attempt/command before selecting a durable
request. It checks scoped provider output, the worker cancellation response and a
later modeld interrupted state. It does not equate these with confirmed remote
cancellation. Mismatched lookups, no output, cancellation failures and completion
races fail the interruption gate. Reconciliation evaluates the actual lookup:
completed records become used with their reported usage; unconfirmed records keep
the original reservation. Reopening and repeating the exact command must not
construct another transport or change the original steps.

**18 offline checks pass**, including the actual bounded driver running against
real local HTTP/SQLite/document reads/downloads with an explicitly substituted
model. This fixture emits no real provider requests and does not certify the
earlier real observations. Per-request interruption/reconciliation counterexamples
use local fake responses. See [GREEN](green.txt) and [verification](verification.json).

The first full run (727 tests) exposed an error in this new test harness: nested
observer cleanup restored the fake transport after the outer patch had ended,
polluting later transport tests (12 errors, two failures). The cleanup order is
fixed and explicitly asserted; 25 combined driver/observation/HTTP transport tests
pass. This failure remains in the verification history and is not a product RED.
Final validation on `1c5780f55c4c41a949e31901fcfaa969d3edfb7d` includes the author's
rebased history and the reviewed S03 runtime: **751 Python tests pass, nine
skipped, zero errors/failures**, and `npm run check` passes. Raw-log hashes and
the retained initial failure are in [verification](verification.json). This
follow-up changes evidence only; no additional real model call was made.

Current 099/100/107 narratives now state their limited or uncertain scope. Original
logs, reported use, failures and the author's authorization claim are preserved;
the claim is not used by this coordinator as authorization for another real call.
Unknown historical token counts remain unknown rather than confirmed zero.

This change does not complete S03 real acceptance, switch the NAS business service,
migrate live data or modify production code. Real model calls in this intervention:
**zero**. Raw full-suite/environment logs remain host-local. The existing dirty
vendor submodule and other developers' checkout/index were preserved.
