# U-086: bind download acceptance to the original material read

2026-11-10. Base PR70 `2ba812f8018b23f7e6f2ba7d0d28c67be28b97a4`;
single codex-home duty implementation, #40 comment290. DSH remains owner.
One 1–2h offline acceptance repair; no new product slice or model spending.

The real download driver currently accepts a candidate containing the synthetic
nonce without requiring any persisted material read. Before using its result
controls, require the current authenticated original AU/Work snapshot to contain
the original candidate and a unique successful `read_document` receipt for the
synthetic material path. Its SHA256 and UTF-8 byte count must equal the actual
material bytes prepared by this driver. The original result must cite that
receipt, and the receipt's attempt must belong to this Work and contain a used
automatic model request. Listing files, another path/digest/attempt, missing or
duplicate receipts, and a non-referenced read cannot pass.

The actual S03 attempt facts are in `work.attempts`. The older `attempt_ids`
field remains empty during automatic execution and cannot authorize or reject
this proof. The Chrome normal control exposed that projection mismatch; use
exactly one matching persisted attempt record, without changing product data.

Only existing Core projection fields are read. No new authority, schema,
transaction, model loop, manual completion, grant or real request is introduced.
The resulting evidence records original references and material hashes, not
document/result bodies. A matching receipt proves the recorded read and source
link; it does not independently prove the next model's full input or real
business quality. Those exits and PR70's separate review remain pending.

RED executes the actual pre-delivery driver block with matching candidate
metadata and missing/substituted read evidence. A normal Unicode-material
control must pass. GREEN adds only a read-only assertion helper and its call,
then verifies Node fault cases and Chrome against real Core/HTTP/SQLite facts.
Current-head full checks and another engineering role's review precede adoption.
Existing unrelated dirty files, index/HEAD and failed evidence are preserved.
