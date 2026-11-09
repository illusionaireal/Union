# Same-run Core restart evidence

Frozen 2026-11-09, before implementation, for #40 comments 242/248.
Actor: single codex-home duty implementer. Online member:
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`; DSH retains #40 and its history/WIP.
Author input: `7493451e385709083b035296d614352f02cd790c`.
Current integration: `4aa020bf6e528d1d9bc6ab28c5aa8b63cc53fe5c`.

One 2–4 hour repair, no additional split: both existing acceptance drivers
must retain and compare the same original Work across a Console restart.
This is an offline assertion repair, not a product authorization change.

- Before and after restart, GET `/api/v1/work` for the fixed original AU.
  Require HTTP 200, `core.work.v1`, original AU, authenticated principal and
  exactly one original Work. A legacy error body is never a valid snapshot.
- Capture current `/api/session` around each read. Require Core protocol and
  principal/service consistency within the read. A normal restart may replace
  service_instance; it must preserve the original principal and AU/Work.
- Require nonempty original step, attempt, command and model request IDs.
  After restart, preserve every original request identity, status, usage,
  connection, reason and budget; reject missing, substituted or extra steps.
  Reordering unrelated JSON keys or the step list is not a change of fact.
  No outstanding reserved step is accepted as settled restart evidence.
- Record distinct persisted request identities and per-request usage/status.
  Unknown usage stays null; never count one run_loop click as one model call.
  Request-identity count is not an independently observed transport-call count:
  these snapshots cannot exclude replay of the same external request ID.
- Save only successfully validated before/after snapshots, and a compact
  comparison summary. Existing result/download and cancellation gates remain.
  No model calls, driver main, host config, identity migration or service switch.
- Old evidence139's unsupported before snapshot remains an historical failure;
  new reads cannot retroactively replace it. Missing original output evidence,
  real page observation and original-command replay remain separate exits.

Validation executes the actual driver snapshot and restart assertion sections
with synthetic successful controls and counterexamples, then pinned npm/Python
and exact-head CI. Another engineering role reviews before adoption. The current
checkout's pre-existing files and regular index remain untouched; this branch
uses a private verification source tree and a separate index in the same Git repo.
