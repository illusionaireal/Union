# U086: recover cancellation when the response body is lost

2026-11-09. Scoped assistance from the single codex-home duty implementer,
online member `c18f0d21-1d63-4e37-af3e-2dbb78d75995`, on #40 comment274.
DSH retains owner/progress/WIP; #60/U106 is already done. Baseline PR63 is
`b446caf2a6507f283836e9009984d49f8c93541d`, containing integration `4aa020b`.
This 1–2 hour repair has one outcome; it does not change product behavior.

The cancel can commit before HTTP 200's response body is interrupted.
PR63 waited on `response.finished()`. The pinned Playwright resolves that
promise for `requestfinished`, but not `requestfailed`, so the driver could
wait forever and never query the saved original command. Its earlier lost
response test aborted before headers and did not cover this case.

[Contract](contract.md) was frozen first. The [HTTP fixture](http-host.py)
truncates a real response after the existing Core transaction commits,
without altering the stored receipt. The unchanged full original-output and
cancel fragment reaches genuine HTTP 200 headers and a failed body transfer,
then fails the bounded [Chrome probe](browser.cjs). The initial unbounded
diagnostic required terminating this test's Node process; it is retained as
a diagnostic, not counted as a completed test. No protected process was stopped.

The helper now observes either terminal event for that same page-generated
request, with listeners installed before the click and removed in `finally`.
On body loss it uses the existing page recovery control and full original GET.
It still rejects an observed HTTP 403, even with a lost body; a fully transferred
malformed or mismatched receipt is not treated as transport loss. It sends
exactly one cancellation and preserves current identity, original request and
unknown reservation checks. It does not certify remote cancellation.

Validation and hashes are in [validation.json](validation.json):

- Unchanged-source actual Chrome/Core HTTP/SQLite RED; four final cases GREEN:
  normal, body interrupted after 200, body interrupted after 403, and a fully
  transferred malformed body. Each uses one fake model request and one fake
  cancel. Successful cases also reopen and query the same durable receipt.
- All eight original PR63 browser scenarios remain GREEN, with eight fake
  model requests and six fake cancels. No real driver main or model ran.
- `npm run check` passes 225 Node / 363 frontend / 37 management checks plus
  types/build. Final Python passes 808 tests / 10 skipped / 0 failures in
  518.997 seconds, with Bun 1.4.2 explicitly enabled. The first full run's
  SDK module-graph error and failed setup diagnostic remain recorded; after
  restoring the consistent pinned SDK paths, the SDK test and full suite pass.
- The new real HTTP fault probe is added to the existing browser CI job.

Only the acceptance helper, controlled probes, CI step and delivery evidence
change. `ai_union`, `web`, `services`, schemas and shared transactions retain
the baseline bytes. The 20 pre-existing files, vendor and normal index remain
untouched; delivery uses a separate task ref and index in this repository.

PR63's independent review5825959782 covers its original head, not this new
increment. This implementer requires another engineering role's review and
all current-head CI before adoption. Author-branch adoption is distinct from
integration into `rewrite/charter-v1`; neither closes #22/#39/#40's real exits.
There are no new real calls, grants, migrations, service switches or changes
to supervisor/configuration/locks. Historical139, actual tool/context/usage
and remote dispatch evidence remain separate, without rerunning real requests.

Follow-up found during source inspection: registration also waits on a
success-only `response.finished()`; its partial-body recovery needs its own
bounded RED and scoped correction. It is not silently included in this change.
