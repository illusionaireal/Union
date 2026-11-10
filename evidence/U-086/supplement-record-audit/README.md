# Review of the original-ID supplement: keep the three runs separate

2026-11-10. Reviewer: the single codex-home duty session, distinct from DSH's
supplement implementation. Actual authenticated board user at readback was
HOME-GOOSE / `cafeef64-ac40-4062-97c1-ac82ece0a379`; that identity does not
make this actor DSH or a product AU member. #40 ownership and progress remain.

**Supplement `02dc3f37a4c0ad0c43e33b1cce1a18db2b2fd556` overstates what
evidence134 establishes.** Its conclusion that the real exit is incomplete
remains correct. This review responds to its new "3 met, 1 partial, 2 open"
classification, not a request to rerun the historical real calls.

The [contract](contract.md) was frozen before the new [record reader](audit.py).
[The report](records.json) binds ten exact Git blobs and separately inventories
evidence127, 134 and 139. No candidate code or driver main was executed.

| Supplement claim | Saved evidence at this exact commit | Correction |
| --- | --- | --- |
| 134 made a single real dispatch | Two distinct model request records: one used, one unknown; known usage subtotal 438/40 | Report the two records and unknown remote invocation count. Do not infer either one or two verified remote calls. |
| Acceptance / modeld interrupted / remote unknown are all recorded | The cancelled step says `model_outcome=unknown`; its reason includes `work_step_interrupted`. The selected files contain no complete modeld interrupted receipt. | Preserve Core cancellation/unknown facts; modeld's actual returned state still needs its original receipt. |
| Full cancel command/POST/GET identities are established | 134 has successful identity-check labels, but its only embedded cancel JSON is truncated; no complete submitted cancel command and paired POST/GET bodies are retained in these inputs. | Say the repaired driver reported identity checks. Independent field-by-field recomputation remains unavailable from these files. |
| The old 127 review binds 134's source/service/run | 127, 134 and 139 have different AUs, principals, request IDs and snapshot hashes | Keep each run's binding separate; the exact hashes in the 127 review do not certify 134's execution source. |
| Original output was never captured | Later 139 contains `original request text observed before cancel` and additional output/identity check labels | Inventory 139 separately and follow its existing review limitations. Neither ignore those records nor upgrade check labels to full real/page acceptance. |

All three cancelled request IDs match their respective check labels; all three
reported usage totals match the *known* saved subtotals. Those positive controls
passed. Cancelled-request usage is absent in all three inputs and remains
unknown. All three before-snapshots lack a successful `core.work.v1` observation.
These are structural checks, not product behavior tests or new model calls.

Publication validation initially rejected the generated report's Windows
CRLF as trailing whitespace (`3ebeabff680c21208538416046b1551639c63de8`,
unpublished). The reader now writes explicit LF; record values are unchanged.
Link, source-hash, privacy and final diff checks pass. Full repository CI is a
separate publication gate and is not claimed by these structural checks.

The newer driver's controlled fixes and evidence139 limitations are already
documented in [final-read combination](../final-read-combination/README.md) and
[original output gate](../original-output-gate/README.md). A historical check
label remains limited evidence; this audit does not claim the driver actually
received a wrong identity or that the product lost a reservation.

Reproduce with the pinned project Python and the author commit fetched:

```text
python -B evidence/U-086/supplement-record-audit/audit.py --output <report.json>
```

Exit 0 means the immutable record audit completed, **not acceptance passed**.
Missing/invalid input exits 2. The reader does not access the network, import
candidate code, modify originals, or obtain records from a live AU. The report
does not assert that additional private records cannot exist.

Disposition: original owner should correct the supplement's classifications
and identify any available complete original receipts and run-specific source
binding. Preserve the old history, unknown usage and missing before-state.
No new inference is authorized or required for that correction. #40/#22 stay
incomplete. This delivery changes only the bounded review and its index;
product, drivers, deployment, ordinary checkout HEAD/index and prior edits are
preserved. New real calls, service switches and migrations: zero.
