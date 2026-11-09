# Observed reader reaches original cancellation recovery

2026-11-09. The codex-home duty implementer fixes the driver composition defect
reported in #40 comment260. DSH remains the owner; this is an assistance
candidate requiring another engineering role's review and current-head CI.

On exact author `abef54404dfd2b440bd602082013e7adda21bb58`, the output gate
validates the principal/service but discards them from `outputObservation`.
The next fragment reads its missing `principal_id`, so even a legitimate
original cancellation fails with `original cancel reference principal_id`.
The prior 147 tests passed because separate cancellation fixtures supplied
that field directly. No product authorization failure is implied.

The [contract](contract.md) preceded the behavioral RED. The new permanent
[composition test](../../../tests/exit22-output-cancel-chain.test.ts) executes
the actual output gate, original-cancel GET and restart fragments together;
it never injects `outputObservation` or executes driver main. Unchanged author
source fails all four cases: normal recovery fails, and the three negative
cases cannot reach their intended boundary. One earlier extraction-marker
fixture error is retained separately and is not counted as behavioral RED.

The repair adds two fields from the already validated observation session:
`principal_id` and `service_instance`. Existing current-reader checks remain
unchanged. The same four tests pass, including changed principal after output,
service change during the receipt read and substituted receipt after restart.
142 related tests and npm check (151 Node, 363 frontend, 37 management, types
and build) pass. Full Python: 808 tests / 10 skips / 0 failures (505.661s),
including the pinned Bun SDK loopback. The skips retain real-model opt-ins,
platform limits and unbuilt modeld release declarations; none count as real
acceptance. Exact source and private-log hashes are in validation.json.

[browser.cjs](browser.cjs) joins the same real driver fragments over actual
Chrome / Core HTTP / SQLite, using [a disposable fake host](http-host.py).
The exact original source fails on the missing principal; the candidate reads
the original receipt and reopens it with a changed service instance. Wrong
Work/attempt/principal, HTTP403 and substituted receipts are rejected. Browser
observation sends zero POSTs. Each host run prepares one fake inference and
one fake cancellation before observation: this is retrospective data-binding
verification, not proof that a user saw live output before cancelling.

```text
node --test tests/exit22-output-cancel-chain.test.ts
node evidence/U-086/reader-binding/browser.cjs
```

Use the pinned Python/Node/Chrome executables in the host environment. To
reproduce browser RED without changing the candidate, supply an exported exact
original driver file as the optional browser-script argument. Only its two
assertion fragments are extracted; the real main is never executed.

The candidate retains original model request IDs, receipt equality, current
authorization and unknown reservations. It adds no raw text or credentials
to evidence. No product/runtime/schema, NAS, supervision or configuration
changes, new real inference, deployment switch or data migration occurred.
Historical139 and the incomplete page journey, real remote dispatch accounting
and #22/#39/#40 acceptance remain separate. All existing checkout dirty files
and the ordinary index are preserved; a task-owned index delivers only this
repair and its evidence on a separate branch.
