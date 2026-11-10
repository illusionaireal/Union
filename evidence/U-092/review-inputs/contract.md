# U-092 review runner input contract

2026-11-10; response to Kanban message135. Actor: the single codex-home
review duty session. This 1–2 hour repair owns the PR76/77 review runners,
not the original owner's U092 product implementation or task claim.

Before importing any candidate code, both runners must check the candidate
against the 20-file source map retained in the lifecycle validation record.
The clean integration commit contains the review evidence, but does not
contain the unpublished recovery implementation or its fixture. Missing
inputs and mismatched source are not product behavior failures.

- Missing files, mismatched bytes, or an invalid manifest produce exit 2 and
  a JSON input diagnosis with zero tests/observations and no model execution.
  Candidate modules must not be imported in these cases.
- The default input is the historical 20-file snapshot. For a repaired
  candidate, the reviewer explicitly supplies a replacement source manifest
  and its SHA256. It must cover the same 20 paths; its bytes must match the
  candidate. The resulting report identifies which source was tested.
- Valid input runs the existing assertions unchanged. Exit 1 remains a
  behavior/test failure, exit 0 means only those bounded synthetic probes
  passed. Preserve the original P1/P2 failures and validation files.
- No source fetching, product code copying, fixture substitution, model
  spending, or deployment is performed by the runners. A manifest records
  identity; it is not a sandbox or product approval.

Acceptance: first observe the clean-candidate import failure as RED, then
verify both runners produce an actionable input diagnosis; reject source
drift before candidate imports; accept explicitly bound revised inputs;
retain the historical lifecycle 1 pass/2 failures and superseded-recovery
2 passes/1 failure when the original snapshot is supplied. Preserve ordinary
checkout files/index and #46 ownership, WIP, and downstream dependencies.
