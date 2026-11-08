# S03 candidate integration

2026-11-08. Integrator: codex-home. Kanban #22 comment #62 records the bounded
integration scope; DSH keeps the original Work card and PR #22 drivers.

The following pending candidates were combined in the existing non-synced
checkout on `codex/s03-combined-integration-20261108`:

| Input | Exact head | Scope |
| --- | --- | --- |
| Integration baseline / merged PR #17 | `bbe8068335c32c04bdcf6d4fa20375245b912cf9` | Durable dispatch, context and late facts |
| PR #24 | `39db061e307accc7410bee6d71c14756abd43fbd` | Preserve parent loop receipts after later admission fails |
| PR #25 | `4bce4919c36e2505d77da7619945ad148d0124d2` | Dispatch schema and code rollback compatibility |
| PR #26/#27 | `9d60a948f5d89123f185b6456553ce7fefe1ed1a` | Core tasks read UI, review evidence and HTTP fixture |

Product sources merged without conflicts. The only conflict was the U-067
evidence index; both entries were retained. The combined source commit is
`e0da6b48a0a6bacce45e84629966b2d0c38be4ba`, tree
`7fed1f0517fa46a609c2b61d77c63c5a4b5e11fd`.
The later evidence commit adds this directory and its index, without changing
that product/test tree. The pre-existing dirty vendor file was preserved and
is not part of the candidate.

## Combined behavior

The [contract](contract.md), [isolated host](host.py) and [browser probe](browser.cjs)
exercise real local HTTP, SQLite and Chrome with an explicit loopback model
double. Two completed turns read a document and create a candidate result.
The first attempt is then stopped at its two-call bound. A different Work
records an interrupted/unknown request. The normal Console is restarted;
repeating the original unknown request does not dispatch again.

Ten checks pass: schema 4 remains readable; the second request receives the
first tool's decoded document body; the stored document digest matches; the
result content, byte count and digest match; all three requests have distinct
identities; the original unknown reservation survives; both Work budgets appear
on the real core route; refresh/reload and three viewport widths work; reads
send no Work POSTs; and a session without its cookie cannot download the result.
This is a candidate artifact, not adopted/delivered business output.

Three initial fixture assumptions were corrected without changing product code:
tool content is a JSON envelope, the first attempt must release its active
directory use before the next attempt, and the download API returns a JSON
envelope containing the persisted content. Those fixture failures are not
product RED/GREEN evidence. One original-probe invocation omitted its required
repository argument and ran no tests; the corrected invocation passes all three.

## Validation and limits

- Python full suite: **723 tests, 8 skipped, passed**, 447.380 seconds.
- `npm run check`: passed, including **220 frontend tests**, 37 management
  tests, 9 action tests, typecheck and build. The existing bundle-size warning remains.
- Original three S03 review probes: passed on the combined tree.
- Ten new combined browser checks: passed.
- Seven existing U-081 browser privacy/download counterexamples: passed on
  the combined tree. Reusing that review script does not make this integrator
  an independent reviewer of the combined runtime changes.

Sanitized results are in [verification.json](verification.json). Windows used
Node 24.19.0 and the already-installed project Python 3.12.10 environment;
no dependency or lockfile changes. Build the console before the browser probe,
and set `UNION_PYTHON` and `UNION_CHROMIUM_PATH` to the host executables:

```sh
node evidence/U-067/combined-integration/browser.cjs
python evidence/U-067/independent-review-probes.py .
```

This branch is a concrete combined candidate for CI/review. **It does not adopt
PR #24/#25/#27 or replace their required separate engineering reviews.** At the
last GitHub read, each of those three inputs had 14 successful current-head
checks; PR #26's old head still had its known Windows fixture failure. The
combined head needs its own CI. Original PRs must be reconciled before merging
any aggregate candidate; do not replay merges or bypass their review gates.

PR #22 remains draft with the latest driver findings assigned to DSH. There
were zero real model calls, no NAS service switch or live data migration, and
no changes to supervisors, host configuration, locks or credentials. This
evidence neither closes full S03 acceptance nor certifies sustained operation.

## 2026-11-08 review response integration

PR #24 now includes `81c113f7f571227aa96a31dca6071683e8c7e07b`, responding to
DSH's messages #26/#27. Rejected parent receipts have `phase: loop-stopped`;
the new schema-3 second-turn failure test retains the completed first call
and unresolved original reservation. Four phase assertions failed before
the two-line implementation. On the PR #24 source, all nine targeted tests,
716 Python tests (eight skips), npm check and the original three probes pass.
The [response](../loop-receipt-fix/review-response.md) also identifies PR #25's
transaction, validation and release boundaries. It is an implementer response,
not independent approval.

This commit merged cleanly into the previous combination as `9f9e6d0`.
On that source, 18 loop/compatibility tests, the three original probes and
npm check (220 frontend tests) pass. The earlier complete 723-test/browser
run remains anchored to its original source; it is not relabeled as a full
run of this new combination. Current-head protected CI is still required.

The new live message #35 reports PR #27 merged by its independent reviewer.
GitHub review `5817709345` was read back at exact `9d60a94`; PR #26 now has
head `875d09ef69c61acffc5e1e87f56f9add76633286` with the same reviewed tree.
Its merge history was added as `31e6b82`, and the entire tree is byte-identical
to tested `9f9e6d0`. This does not merge PR #26 into the integration branch;
that PR's current-head CI must pass first. PR #24/#25 and their combination
still need a different engineering role's acceptance. PR #22 remains with
DSH. See [incremental verification](review-response-verification.json).

## 2026-11-08 adopted UI baseline and new CI fixture failure

GitHub confirms PR #26 was merged as `90de860e653673e5ecdc74205739011812c193ef`.
The combination includes that actual history at `4494b75`; its entire tree is
identical to `9e1ac0e`. PR #26/#27 must not be merged again.

On `4494b75`, Windows job `128721896081` failed in the separate V1 creation
helper's five-second socket wait, before the responsibility test assertions.
The [fixture follow-up](../core-http-fixture/README.md) retains that failure,
the real delayed-response RED/GREEN and original-request recovery evidence.
It changes the default fixture wait to 30 seconds and keeps explicit timeout
overrides, single POST behavior and all product checks. PR #24/#25 and this
combination still need independent adoption review and current-head CI.

The fixture candidate's completed local validation is now indexed in
[verification.json](../core-http-fixture/verification.json): Python 725 tests
(eight skips), npm check and the original three probes pass. Resumption adds
two delayed-response checks and 40 affected HTTP/identity/responsibility checks,
all passing. The earlier full runs belong to this unchanged product/helper
source; the original failed Windows job is retained, and the published head
still needs its own CI and independent adoption review.
