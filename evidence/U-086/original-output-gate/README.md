# Bound original-output acceptance repair

The single codex-home duty implementer addresses #40 comment237; scope and
original owner retention were acknowledged by GET200 comment238. This is a
candidate requiring another engineering role's review, not an independent
approval or completion of the real parent card.

Author `75c7a946ea459861fa60d9831b3b1fedfa1376ed` already includes U108.
Its interrupt driver nevertheless accepts a failed/missing events endpoint,
any nonempty event list, and zero `ownEvents`. The public Core projection
intentionally puts model_request_id in the envelope, not individual events.
Evidence138 records own-matched=0 and an unsupported legacy before-snapshot.
That record cannot establish the claimed complete before/after acceptance.
Original evidence and the author's other driver behavior remain untouched.

After freezing [the contract](contract.md), the actual unmodified assertion
block produced **1 pass / 30 failures** across 31 Node tests (including the
parent subtest container). The ordinary public text control passed; the
counterexamples were false acceptance, not import or dependency failures.
The same suite passes **31/31** on this candidate. An intermediate validation
had a VM-only missing TextEncoder global in three controls; it is retained
separately and fixed in the test sandbox, not labelled a product failure.

The driver now binds the response to the original AU, Work, attempt, step,
command, model request, connection, principal and service; follows the cursor
past filtered pages; rejects invalid ordering; and requires actual nonempty
text before cancellation. A hash and UTF-8 byte count preserve the observation
reference without storing raw text. Missing U108 is a failed acceptance gate.

Run `node --test tests/exit22b-original-output.test.ts`. It extracts only the
bounded gate into a VM using synthetic GET responses. It never executes the
driver main, launches a browser/host, cancels a real request or invokes a model.
No product authorization, execution, reservation or accounting code changes.

Exact source/log hashes and full validation are recorded in validation.json.
Page-visible real observation, same-run valid restart snapshots, remote call
counts, billing and the complete #39/#40/#22 exits remain separate. This
candidate does not authorize another real run to refresh historical evidence.

Full prepared-source validation: 808 Python tests / 10 skipped /0 failures (505.590s); npm check with363 frontend,51 Node and37 management cases passed. Management render/check and syntax checks passed. Final evidence-only updates preserve the tested driver and test blobs. Current-head CI and another role review are still required before adoption.
