# Original-record audit of the November 10 supplement

Frozen before implementing the record reader. Scope: a bounded independent
review of DSH's supplement at `02dc3f37a4c0ad0c43e33b1cce1a18db2b2fd556`,
responding to #40 comments339/341 and their subsequent source revision.
Estimated effort: 0.5–1 hour; one evidence-consistency result, no split.
Original owner, work in progress and real acceptance remain unchanged.

Read immutable Git blobs only. Do not run the driver, import candidate code,
connect to modeld, or query/modify a live AU. Record the commit, blob SHA256s,
original request identities and missing records. Missing input is a reader
error, not a product failure. This is a structural review, not product TDD.

1. Distinguish saved request records from verified remote invocation counts.
   A completed request plus a different unknown request cannot substantiate
   the supplement's unqualified "single real dispatch" statement.
2. Keep cancellation acceptance, modeld's returned state and remote outcome
   separate. A Core step's reason containing `work_step_interrupted` with
   `model_outcome=unknown` is not a saved modeld `status=interrupted` receipt.
3. Distinguish successful driver check labels from full original command,
   POST and GET receipts. Truncated JSON cannot reconstruct their identities.
   Existing label evidence remains useful; do not label it absent.
4. Bind each run separately. A review of evidence127's exact source/input
   hashes cannot certify evidence134's different AU, principal, request IDs
   and snapshot hash. Later evidence139 must be inventoried separately too.
5. Preserve known usage subtotals and unknown cancelled-request usage. An
   unsupported before-snapshot is missing evidence; do not invent it, zero
   unknown usage, or upgrade a persisted after-state to zero-redispatch proof.

The output reports documentary support and limitations, not true/false remote
execution facts. No real-call count may be inferred from this audit.
