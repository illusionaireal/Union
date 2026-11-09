# Original output before interrupt acceptance

Frozen 2026-11-09 before behavior changes. Input: author
`75c7a946ea459861fa60d9831b3b1fedfa1376ed`, comment237 on #40.
Integration independently read as `7fe50c213adcf2d826109b6fe272f31ee09bccf8`.
Actor: the single codex-home duty implementation session; DSH keeps #40.
One 2–4 hour scoped repair: make the interrupt driver's output assertion
enforce its existing acceptance contract. No extra agent or model invocation.

- Current U108 exposes `core.work-events.v1`. Absence, 401/403 and failed reads
  cannot satisfy this acceptance exit. No successful optional-capability path.
- Before cancel, require a successful Core response for the original AU, Work,
  attempt, step, loop command and model request. Bind principal/service and the
  original connection fields from the current authenticated Core snapshot.
- The public events omit per-event request_id intentionally. Use the validated
  response envelope, not a fabricated event field. Require nonempty text_delta
  output; lifecycle, tool-only, empty or unrelated events are insufficient.
- Follow the existing cursor through pages, including pages containing only
  filtered events. Reject regressing/malformed cursors or invalid sequences;
  never switch request identities while waiting. Only GETs are added.
- Preserve an observation summary with original identities, cursor and SHA256
  of observed UTF-8 text; do not publish raw model text or private host data.
- This repairs the offline assertion. It does not prove page-visible real
  output, cancellation delivery, same-run restart persistence, call counts or
  billing. Comment237's evidence138 has an unsupported legacy before-snapshot;
  that historical file and its claims remain unchanged and cannot close #40.

Validation: execute the actual bounded assertion block in a synthetic VM with
successful controls and counterexamples, first on unchanged source (RED), then
on the candidate (GREEN). Test API event projection separately as relevant;
run pinned npm/Python and current-head CI. No acceptance-driver main executes.
The author/another engineering role reviews this implementation before use.
