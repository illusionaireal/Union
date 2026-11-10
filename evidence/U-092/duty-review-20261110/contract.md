# U-092 independent prepublication review

2026-11-10. Reviewer: the single codex-home deployment/integration duty
session, distinct from implementation session `01a1c217`. #46 remains with
its original owner; this review neither claims the card nor adopts the code.

The author's unpublished candidate is based on `63c4030ec1c520824c00633e42b45019a3e9c533`.
A read-only copy of all 20 changed/new source files was checked before and
after copying. Its manifest SHA256 is
`37b49c71de59f9cdad4ab0358a703df6deaa5f980336373a6eea3d8947c30148`
(the saved manifest bytes, including their original Windows line endings).
This identifies a source snapshot, not a published or CI-tested commit.

Before new probes, freeze this review boundary from the author's U-092
contract clauses 2 and 6 and ADR-0009: a service that has closed/released its
execution ownership must not begin another model dispatch. Already committed
reservations and original request IDs remain available for current-service
reconciliation. Closing before intent commits must not create new intent;
closing after intent commits must not erase that intent or dispatch it.

Probe the actual WorkService with the existing HTTP/SQLite fixture and an
explicit fake transport. Close the old Console during channel construction
and at the existing pre-transport material check; do not edit product code or
manufacture a failure by removing working guards. A live-service control must
still complete one dispatch. Only test hosts are closed. No real inference,
production restart, migration or author-checkout/index write is allowed.

Review scope is a bounded independent check, approximately 1–2 hours. The
author owns product fixes, browser completion, full validation and publication;
this review will provide executable failures with source hashes.
