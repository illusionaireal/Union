# U108 independent review: changes requested

2026-11-09. Reviewed PR50 at `69af6a61e9f3f24182226239d242d26a912a94d1`;
initial probes used `8bcf5da08a91a6355343f7544e3289887de4d04d`. Reviewer:
the single codex-home duty session, independent of the cloud implementation
session. Online member `c18f0d21-1d63-4e37-af3e-2dbb78d75995` is recorded
separately from that engineering actor. #62's owner remains chatGPT-online;
#40/#22 and real acceptance remain open.

## P1: truncation disables authority revalidation

`WorkStream.tsx` schedules another poll only while `!limited.current`, and
disables the manual query button when truncated. The shown partial text then
has no continuing session or original-grant check. A background grant
revocation, governance handoff or session expiry cannot clear it without an
unrelated page refresh. `WorkPanel` itself does not poll its projection.

This violates the frozen requirement to revalidate read authority while the
output is expanded. An output size limit does not extend read permission.
Keep the display bounded while continuing authorized original-request checks;
clear existing text on the same forbidden/incompatible outcomes. Cover both
server page truncation and the browser's aggregate character/event caps. Do
not change model dispatch, accounting or the read-authorization policy.

Independent DOM probes, on both exact heads: one nontruncated terminal-output
control passes; truncated output followed by HTTP403 and HTTP401 both fail.
After ten seconds of fake-clock progression, the private prefix is still in
the DOM and no new check occurs. Product source was unchanged for every probe.

## Verification and fixture limitation

- Eight author HTTP/SQLite tests pass on unchanged backend bytes.
- Three additional independent HTTP checks pass: changing an unrelated default
  preserves the original connection; remote revocation during event GET and
  governance handoff during that GET prevent disclosure. Observation does not
  add model POSTs or rewrite Work accounting.
- The actual Chrome script at `69af6a6` passes all 17 assertions, including
  1440/390/320px layouts, output before cancellation, same cursor, unknown
  reservation retention and original-ID reload/restart. It makes exactly one
  fake model request and one cancellation. [Checks](chrome-checks.json).
- Its host calls `setUp`/`tearDown` directly but omits `doCleanups`; the account
  service's stop and temporary-directory cleanup live in `addCleanup`.
  Windows reports `console.lock` PermissionError during interpreter cleanup.
  The parent returns exit zero without awaiting/validating child completion.
  Record this separately from the 17 passing browser assertions. The fixture
  should run its registered cleanup and propagate shutdown failures.

This review did not run full local Python/npm or claim current CI success.
The initial `8bcf5da` browser CI failure remains history; the later layout change
does not resolve the reproduced P1. Exact source and private-log hashes are in
[verification.json](verification.json). One snapshot-update launcher attempt
used a wrong working directory; it was corrected and source bytes reverified
before the current-head probes/build/browser. That launcher error is not a
product failure. No real model calls, deployment, migration or business exit.

## Reproduce without real services

In an isolated snapshot of the reviewed head with the locked dependencies:

1. Copy `WorkStream.independent-review.test.tsx` into
   `web/console/src/features/work/` and run it with that workspace's Vitest.
   Expected before repair: **1 PASS / 2 FAIL**.
2. Copy `http_probes.py` to `tests/u108_independent_review.py`; run
   `python -m unittest tests.u108_independent_review -v`.
   Expected: **3 PASS**. Each creates its own loopback double.
3. Build the console and run `node scripts/u108-work-events-browser.cjs` with
   the pinned Python and an installed Chrome. Preserve the shutdown stderr
   separately from `checks.json` and the parent exit status.

The probes are review evidence, not frozen failing CI expectations. After the
author's repair, retain this RED history and rerun them expecting all to pass;
check the exact new head's CI and independent permission review before adoption.
