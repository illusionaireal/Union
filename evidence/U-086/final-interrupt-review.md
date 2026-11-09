# Final interrupt evidence: independent review of 1e490d0

2026-11-09. Reviewed author commit
`1e490d074d0b4e91291860d742244af55ed81d88`, after the PR44 adoption. Reviewer:
the single codex-home duty session, online member
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`. Fresh Kanban revision 583 and comment
189 preserve DSH's #40 ownership and the unfinished parent acceptance.

**The final rerun does not establish the complete 22-C exit.** Its saved evidence
does establish a matching cancelled request ID, an unknown step with reserved=1
after restart, and a preceding completed step. The new probes expose missing
assertions; they do not prove that the product actually returned a wrong identity
or lost a reservation in this real run.

## New reproducible counterexamples

The [frozen review contract](final-interrupt-review-contract.md) precedes the
[offline probes](final-interrupt-review-probes.py). They extract three blocks
from the exact author driver without executing its main, host or real transport.
Six tests: **three failures, three passing controls, zero execution errors**.

During review, the author merged the host repair into
`d3823e8f76db3eda5216b836af0decdeaec05d02`. Fetch and GitHub both confirmed that
head. Its driver and all four inspected evidence inputs have the same SHA256s;
running the six probes on that exact new head again gives three failures, three
controls passing and zero errors. PR45 was automatically marked merged into the
author branch. Integration remains `902b429`; this is not reviewed adoption into
`rewrite/charter-v1`, and PR45 still has no independent review record at readback.
Author comment 190 subsequently acknowledges the host/download findings and
reserves driver/claim corrections for the next candidate. Its successful host
tests do not retroactively change the connection used by the historical run.
These records predate the repair and cannot establish that they exercised the
connection/grant preserved by the repaired host.

| Boundary | Observed driver behavior | Required author correction |
| --- | --- | --- |
| Output before cancelling the original request | A completed first step plus a reserved second step, with no output from the second request, triggers cancellation. | Observe and retain output/events tied to the second request before cancelling it. Prior-step output and a reservation are insufficient. |
| Cancel response identity | HTTP200/succeeded/cancel_accepted=true for another AU, command, attempt, step and model request passes both checks. | Retain the submitted cancel command ID and compare all original identities with the response and original GET. |
| Reservation after restart | The unchanged unknown step/reason passes with reserved=0 after restart. | Compare successful same-run Core Work reads, including original identity and the unresolved reservation. |

Controls confirm no reservation does not trigger cancellation, a normal-shaped
cancel response is accepted, and unchanged unknown/reserved=1 is accepted.
The first probe checks the driver's actual cancellation trigger, not whether
the model produced output elsewhere. The last two execute its existing check
blocks with synthetic response/snapshot values. They are deterministic offline
counterexamples to the acceptance assertions, not end-to-end product tests.

## What the new saved records actually show

The [machine-readable review](final-interrupt-review.json) retains input SHA256s
and request IDs. Final evidence has two distinct model request records:

- Step 1: `used`, input/output usage **438/43**, one `read_document` tool record.
- Step 2: `unknown`, the request ID matches `checks-final-head.json`; usage is
  absent and remains **unknown**. Final budget is used=1/reserved=1/max_calls=3.

The 438/43 aggregate is the known first-step subtotal, not complete usage for
both requests. The old README's single-call/used=0 description applies only to
its earlier snapshot and must not describe the final rerun. These two saved runs
contain three distinct request records in different AUs; they must remain separate
historical runs. This review does not independently verify remote invocation or
billing counts, and does not infer zero usage for the cancelled request.

`snapshot-before-restart.json` is still an `unsupported_capability` error from
the legacy snapshot endpoint. The final commit adds no corresponding
`snapshot-before-restart-final-head.json`. The old and final after-snapshots have
different AU identities. Therefore neither pairing establishes same-run
before/after preservation. The final after-snapshot itself remains useful limited
evidence; it is not rejected merely because an earlier read failed.

The driver still cancels through page-evaluated API code, waits only for a
reservation, and saves no original-request output event or full cancel/GET
receipt. The truncated check label cannot reconstruct those missing facts.
Its Console restart does not itself demonstrate original-command replay with
zero new dispatches. No output history should be invented to fill these gaps.

## Reproduction and disposition

With the pinned Node on PATH and the exact Git object available:

```text
python evidence/U-086/final-interrupt-review-probes.py 1e490d074d0b4e91291860d742244af55ed81d88
```

Expected exit is **1**, with the three named counterexample failures. A parser,
missing Git object or runtime error is not a valid reproduction. The historical
driver remains unmodified, so this review does not manufacture a GREEN result.

The review branch's ordinary checks pass: Python **792 tests, 9 skipped, zero
failures** (491.522 seconds); npm check **343 frontend, 37 management, 9 action
tests**, types and build. Management render leaves generated files unchanged.
Product and standard-test bytes equal integration `902b429`; this suite does not
include the author's unadopted host/driver changes. [Validation and private-log
hashes](final-interrupt-validation.json) separate these passing repository checks
from the three intentionally retained acceptance-probe failures.

DSH retains the driver repairs and evidence/127–128. Correct the assertions and
claims offline, then obtain any available missing records by the original IDs;
if historical output or same-run observations were not captured, keep that
acceptance condition unproven. New paid requests need separate user authorization.

PR45's connection-preserving host repair is a separate implementation by this
session, now in the author branch and awaiting another engineering role's review
before integration adoption. These probes do not approve
that repair or the author's broader evidence branch. This review changes no
product, driver, host, schema, deployment, original evidence or task ownership.
New real model calls: **0**; service switches and migrations: **0**.
