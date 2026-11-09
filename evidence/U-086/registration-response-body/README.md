# U-086: recover a registration with a truncated response

2026-11-09; #40 comment276, single codex-home duty implementer. Base
`bef1e54fca6f02a347c6954a9a13a2aa9b53cfc7` retains PR64's pending cancel fix.
Integration was read back as `4aa020bf6e528d1d9bc6ab28c5aa8b63cc53fe5c`.
DSH retains #40; #60 is already done via PR39 and was not reimplemented.

Both acceptance drivers could hang after the Core had committed `start_work`
and sent HTTP 200 headers but the response body failed. They also discarded a
complete invalid POST receipt, allowing a subsequent good GET to hide the
failure. The [contract](contract.md) was frozen before the implementation.

The unchanged helper blob `add995d4f2b3319a8d6529c89d1457d4749490a2`
passed two normal controls and failed eight new cases. The
[browser probe](browser.cjs) runs each full original registration prefix against
actual Chromium/Core HTTP/SQLite; [the host](http-host.py) faults only the
response after commit, preserving the stored facts. A 15-second bound exposes
the success-only Playwright wait without hanging the test process. Known 403
must fail for its status, not merely time out. Complete malformed/mismatched
POST bodies must reject instead of proceeding to preparation.

The helper listens for the exact request's finished/failed event before reload,
uses the existing original-ID query control, and validates both the receipt and
current principal/service/AU/Work. A complete valid POST must match the GET;
known HTTP denial and complete invalid responses stop acceptance. Listeners
are removed in `finally`. No substitute registration or direct API recovery
is issued; success still prepares exactly one attempt on the original Work.

Validation and source/log hashes are in [validation.json](validation.json):

- Ten new actual Chrome/HTTP/SQLite scenarios pass across the two drivers:
  normal, truncated 200, truncated 403, malformed complete body and wrong Work.
- All sixteen original registration browser scenarios pass, including lost
  headers, delayed transport, missing controls and identity/receipt rejection.
- npm check passes 225 Node, 363 frontend and 37 management tests, types/build.
- The explicit Bun 1.4.2 SDK/HTTP check passes with two controlled loopback
  requests and zero real calls. Registration probes make zero model requests.
- Full Python passes 808 tests / 11 skipped / zero errors or failures
  (516.325 seconds). The SDK test skipped by the full-suite environment was
  explicitly run and passed separately above. Final management/render checks pass.

Only this acceptance helper, fault probes, the existing browser CI step and
delivery evidence change. Core application/frontend/model-service code,
transactions and schemas retain the baseline bytes. Local source validation
uses a Git export because the checkout contains twenty pre-existing files that
overlap later task inputs; the task ref and separate index belong to the same
repository. Those files, the normal index and dirty vendor are preserved.

This is an implementation candidate requiring another engineering role's
review and exact-head CI. PR64 review and adoption remain separate; author
branch adoption is not `rewrite/charter-v1` adoption. No real driver main or
real inference ran. #22/#39/#40 real acceptance, historical failures, unknown
results and owner/WIP remain; no new grants, migration, business switch or
supervisor/configuration/schedule/agent-state/lock changes occurred.
