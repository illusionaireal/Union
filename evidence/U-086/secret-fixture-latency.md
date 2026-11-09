# U-086: delayed safe output and review harness verification

2026-11-09. Implementation actor: the single codex-home duty session; online
member `c18f0d21-1d63-4e37-af3e-2dbb78d75995`. Scope was confirmed by HTTP 200
readback of #40 comment 208. DSH retains the original card and real acceptance.
Branch: `codex/u086-secret-fixture-latency`; integration base `a401d2b`.

## Credential fixture repair

PR48 at `23aeb36` has a failed Windows model-service job
[128957645080](https://github.com/illusionaireal/Union/actions/runs/42554682298/job/128957645080).
The safe response had native events and one synthetic provider POST, but no
final result/usage and `interrupted/provider_result_unconfirmed`. Another
Windows job on the same head passed. The annotations do not disclose the
underlying provider exception, so the exact historical cause remains unknown.

After freezing the [timing contract](secret-fixture-latency-contract.md), the
ordinary synthetic provider sent safe text, then waited 1.2 seconds before its
finish/usage frames. With the original fixture's one-second idle and
three-second total deadline, the existing completed/output/usage assertions
failed: 47 pass, one fail. The result matched the CI failure signature, without
changing the product or weakening the test assertion.

The fixture now uses five-second first-event/idle and fifteen-second total
request limits, with a twenty-second observation bound. The delayed response
remains in the suite as a regression. The stream timer is cancelled on abort.
The dedicated kernel timeout test still uses its short deadline and passes.
All input/output secrecy, original events, usage, cancellation, one-dispatch
and zero-external-call assertions remain unchanged. Product, vendor and CI
configuration bytes are unchanged.

Validation and source/log hashes are in
[secret-fixture-latency-validation.json](secret-fixture-latency-validation.json).
Focused security plus dedicated timeout: 50 pass. Full model-service suite:
89 pass. npm check: 343 frontend, 37 management and nine action checks, types
and build passed. Python: 792 tests, eight skipped, zero failures (511.352s).
Exact-head CI is recorded separately; no historical passed run substitutes for
current CI.

## Reply to the asynchronous-harness finding

The author's `970144a` demonstration in evidence/132 calls
`vm.runInNewContext` without awaiting it. Both actual review VMs in adopted
`a401d2b` await that call inside their `try`. Their exact source was extracted
without importing or running an author driver.

[Eight executable controls](review-await-probes.py) verify that both VMs reject
synchronous and post-await assertion failures, accept a successful awaited
assertion, and report a post-await ReferenceError separately with exit 2.
The [recorded results and hashes](review-await-validation.json) also execute
the exact download REOPEN block from `970144a`: both the original adopted
result and a different adopted/delivered result pass its two checks. That
block still uses `some(status === 'adopted')`, with no original ID/digest or
delivered-result binding. This is a remaining author assertion gap, not an
unhandled-Promise result from the actual harness. The evidence/132 history is
preserved. These controls do not validate the whole driver or real acceptance.

Pre-publication fetch found newer author head `f4bd52d`, which merges the host
candidate without changing the download driver. The same eight controls and
two reopen observations were checked at that exact head, with the same result;
see [latest readback](review-await-latest-validation.json). This author-branch
merge is not adoption of PR48 into `rewrite/charter-v1`.

The pre-existing uncommitted count-correction files and U-086 README edits are
preserved and excluded from this delivery. The arbitrary check-count issue is
separate from these exact-VM controls.

## Integration boundary

This candidate repairs a test fixture only. PR48's independently reviewed
host remains a separate candidate until its current checks pass. No new
authority, identity, production timeout or credential policy is introduced.
The Work request's own output observation remains a missing controlled
engineering prerequisite under #40 comment 202; cancellation delivery alone
does not prove output was observed. No real model call, service switch,
migration or closure of #22/#39/#40 is included.

The missing observation result is now execution child #62 / U-108, created
and linked in fresh board revision 619. It is ready and unassigned, estimated
6–8 focused engineering hours; its prerequisites #20/#21/#24/#38/#51 were
complete at that read. Parent #40 retains DSH and progress/WIP, with #62 as a
real prerequisite. The dependency graph was checked for cycles. This is a
creation/readback record, not an offline claim or evidence of implementation.
