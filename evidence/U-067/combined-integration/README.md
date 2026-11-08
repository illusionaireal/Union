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
