# U086: cancel the observed original request through the Core page

Frozen 2026-11-09 before behavior edits. Base PR62
`e6a8b86879f5712020d0f56cb1714d711754d95c`, descendant of integration
`4aa020bf6e528d1d9bc6ab28c5aa8b63cc53fe5c`. Implementer: the single codex-home
duty session, online user `c18f0d21-1d63-4e37-af3e-2dbb78d75995`.
#40 remains DSH's progress/WIP; #60 is already done. This 2–4 hour driver
repair has one independently verifiable result and needs no additional split.

- Only after the existing original-output gate succeeds, click the original
  Work's actual `取消本次执行` control. Capture exactly one page-generated
  cancel_step command and bind AU, Work, step, original request, principal,
  service and current version. No direct POST fallback or replacement ID.
- Missing/disabled controls, absent output, changed identities, wrong receipt,
  rejected command or HTTP401/403 cannot earn page acceptance. A successful
  command does not establish remote cancellation or release unknown usage.
- Wait for that transmission to end, including response loss. Refresh, locate
  the original Work's `原取消请求`, check its stored command ID, and click its
  `查询原请求` control. A lost POST is recovered by GET, never reissued.
- Validate the same complete durable cancel receipt through existing
  readCancelEvidence; keep current session checks before and after reads.
  The pre-action service must remain current for this operation; a later
  deliberate service restart follows the existing restart contract.
- Preserve the output envelope/cursor/UTF-8 digest gate, original command GET,
  before/after snapshots, request/usage/reservation checks and PR62 registration.
  Keep command acceptance, delivery observation and remote fact distinct.
- Tests execute exact driver fragments, never its real main. A disposable
  Core HTTP/SQLite host supplies one explicit fake streaming model request;
  record fake calls/cancels separately. Actual Chrome verifies controls and
  response-loss recovery; Node checks run in normal CI. Run npm/Python gates.

No product, schema, governance transaction, supervisor or credential changes.
No real model calls, grants, migration, service switch or sustained operation.
Exact-head CI and another engineering role's review remain required; this
implementation session does not independently approve itself or close the
real #22/#39/#40 exits. Existing dirty files and normal index are preserved.
