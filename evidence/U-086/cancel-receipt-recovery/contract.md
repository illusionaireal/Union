# Original cancel receipt across restart

Frozen 2026-11-09 before implementation. Input: author/PR57 head
`9d7fe98ea9e790d89f16f6a128af949ecda8ccb8`; current integration
`4aa020bf6e528d1d9bc6ab28c5aa8b63cc53fe5c`. Actor: single codex-home duty
implementer, online member `c18f0d21-1d63-4e37-af3e-2dbb78d75995`.
DSH retains #40, its history and WIP. One 2–4h assistance outcome: make the
existing interrupt driver prove its original cancel GET survives restart.

- Use only GETs for evidence; never replay cancel/run commands or dispatch.
- Before restart and after reconnect, require HTTP200 for session, original
  Work and original cancel receipt. Pin AU/Work/cancel/step/attempt/model request,
  original step command and connection, and the original authenticated principal.
  Session/service must remain consistent within each observation; normal restart
  may change service_instance between observations.
- The public cancel receipt has no Work/attempt fields. Bind its step/model IDs
  through the uniquely matching original Work step, not invented receipt fields.
  Require kind=cancel_step, succeeded/applied, original actor and command/AU,
  real versions, delivered cancel_accepted=true and matching delivery observation.
  This proves intent and delivery only, never remote execution or release.
- Compare each GET receipt with the original POST receipt, and the before/after
  GET receipts with each other. Reject missing, substituted, rejected, changed or
  unreadable receipts. Preserve failed evidence; do not claim a successful exit.
- Save a compact original identity/receipt summary only after validation. Existing
  output gate and request/usage/budget snapshot comparisons remain in force.
- This is a driver assertion repair. It cannot reconstruct evidence139's invalid
  historical before snapshot, prove visible page text, or exclude repeated external
  dispatch under one request ID. Those real exits remain separate and incomplete.

Validation runs the actual driver GET assertion before changes (meaningful RED),
then positive and negative cases including wrong HTTP/scope/identity/status and
post-restart receipt loss. Actual Chrome → Core HTTP → SQLite uses one fake request
and one fake cancel, with zero added POSTs during observations. Run pinned full
checks and exact-head CI. Another engineering role must review this implementation;
the implementation session does not independently approve it.
