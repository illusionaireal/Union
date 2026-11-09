# U-108 / #62: original Work output observation

Frozen before behavior code, 2026-11-09. Baseline a401d2ba3469b48b3125b749c57c21b756536bbf.
Implementation actor: this Codex cloud session; online member chatGPT-online
54f3ed9e-817b-482a-90c1-d46bfc01728c. Kanban claim ready v1 -> progress v2
succeeded. One independently verifiable 6–8 hour UI/API/read/recovery result;
do not split its authorization boundary across independently adopted layers.

## Read authority and origin

- GET `/api/v1/work/events?organization_id=…&work_id=…&step_ref=…&after=0`
  selects the saved automatic step, never a browser-supplied model request ID.
  Bind AU/Work/attempt/step/original command/model_request and original connection
  id/revision/profile/model/grant_ref/grant_revision/output/task limits.
- Only the current AU governor may read unadopted partial text. Session and
  current local role are checked before and after remote GETs. The original
  connection must still exist, be enabled and match those saved scope fields.
  Changing the default alone, a finished attempt or loss of *new-action*
  eligibility does not revoke this read permission. Handoff, local connection
  revision/disable or current original grant revocation/version mismatch does.
- Use the configured product modeld client, existing original request GET and
  events/cursor journal. Check the current original grant and the remote
  request's exact AU/id and `action_authorized=true` around event reads. A
  cancelled/interrupted request whose modeld action authorization is false is
  not readable; its Work/usage/unknown reservation facts remain intact.
- No account/AU lock across network calls. AU snapshots use read-only SQLite
  transactions; GET never creates tables, updates reservations, reconciles,
  adopts, creates grants, dispatches or starts another execution loop.

## Projection and browser

- `core.work-events.v1` response identifies all original objects, current
  principal/service, connection scope, remote state and persisted-modeld source.
  Only text_delta text and read_document tool-call names are public. Native,
  reasoning, tool arguments, provider diagnostics and private configuration are
  excluded. Text is partial evidence, not a result, remote-stop proof or usage.
- Nonnegative safe-integer cursor, at most 500 raw events per page, same-sequence
  identical events deduplicated, conflicts/wrong IDs fail closed. Cursor passes
  private events too; full raw pages signal more pages. Display is explicitly
  bounded/truncated (64Ki chars/page, 256Ki chars/20k entries in browser).
  Clarification after independent review 223/227: reaching any display limit
  stops event-body loading only. Continue GET with `authorization_only=1` at
  the same saved origin/cursor. It performs all current session/local/remote
  checks without calling modeld events and returns an empty event projection
  with `authorization_only=true`. Temporary failure permits metadata-only
  retry; 401/403 still clears retained text. The ordinary response marks false.
- One explicitly expanded original step is polled. Selection stays pinned
  to the entire original identity, including connection scope, when later steps
  arrive, the original disappears or the same step_ref changes source; do not
  silently switch.
  Temporary read failure retains the same cursor and labels disconnected.
  Refresh/restart starts at zero using only GET, never replaying execution.
- Validate current session before/after every response and all original scope
  fields before display. Scope/connection changes, 401/403 or incompatible
  events clear text and cursor; abort/ignore late replies. Even after a terminal
  response, periodically revalidate read eligibility while text is expanded.
  Collapse/unmount stops reads; text stays only in component memory, never
  local/session storage or query caches. Existing cancel control is retained.

## Delivery

Meaningful HTTP and DOM RED on original source, then minimal GREEN; actual
loopback HTTP/SQLite + Chromium partial-output -> existing cancel and same-ID
reload/restart checks; faults, cursor/paging and permission races; affected
regressions, full Python/npm, accurate-head CI and another engineering role's
identity/permission review. Record initial failures rather than erase them.
Only controlled doubles are authorized here; real models/deployment/migration
remain zero. Parent #40/#22, #39 and other owners stay unfinished/unchanged.
