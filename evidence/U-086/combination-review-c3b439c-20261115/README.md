# U-086 combination review: c3b439c

2026-11-15. The two product changes pass independent controlled review. A catalog
profile mismatch no longer prevents the session listing from loading healthy AUs;
direct access still rejects an inconsistent AU, damaged creation audit stays 409,
and scoped visibility is preserved. This does not establish the cause of historical
117-byte snapshots or complete the real cancellation/replay acceptance.

Candidate `c3b439c20dc235d690118cdbea15c7bcf6037601`, tree
`088839418834595a409e72dc14bbad68cb1b03d6`, against integration
`fa77339efbf07e9c9e41482a3376d4c8337f910a`. All 2,410 Git blobs matched
the existing isolated snapshot before execution and stayed unchanged afterward.
The product files match previously reviewed `5545d4f` byte for byte.

The unchanged independent HTTP/catalog probes were rebound to current inputs:
4/4 passed, including both real persisted mismatches and healthy/scoped controls.
The unchanged cancellation-fact counterexamples passed 7/7; unknown local results
no longer claim a modeld interruption. Current driver supplies no modeld receipt,
so remote outcome and missing usage remain unknown. The 36 affected Python tests
passed with one host symlink skip; real Chrome creation/reopen/restart checks
passed 30/30 with no real provider calls. Existing full npm (37 management,
359 Node, 363 frontend) and Python (857, 9 skipped, zero failures/errors) logs
were located and matched against the adopted PR92 evidence digests. Current
candidate and integration CI each passed 7/7. PR checks remain a separate gate.

The reviewer did not implement the two product changes. The PR92 fixture boundary
repair is relied on only with DSH/HOME-GOOSE independent comments 457/458 and its
already verified 14/14 CI; this review does not relabel that repair as self-approved.
Author comments 460/461 provide the explicit current combination delivery.

No schema or persistence writer changed. Directory resolution, AU identity,
governance projection and read-only storage remain in force. Matching localized
error strings is existing implementation coupling, not a new public error-code
contract. No real model, production write, migration or deployment was executed.
#40/#22 owner, WIP, history and unfinished real acceptance remain unchanged.

Inputs/results: [contract](contract.md), [source binding](source-manifest.json),
[validation](validation.json). Unchanged runnable probes and current bindings are included in
[session review](session/probes.py) and
[cancellation review](cancel/cancel-facts-probes.cjs). Raw test logs stay in
this run's private host evidence.
Historical failure records remain unmodified.
