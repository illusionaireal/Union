# Final download read: combination regression contract

2026-11-09, #40, single codex-home duty session. DSH retains the card.
This continues independent review 5823560248/comment252 and DSH's fix
`1bd324a2ed32229f0673cccf14705cb784a9bb4d`, combined with PR58
`b293c6266f1a337ff58b64a8a62ee94b348656da` (independently reviewed by DSH,
online message101). No product authorization or execution contract changes.

The last download Work GET must be surrounded by the existing Core
session/Work/session validation. A principal or service change, or session
expiry, while that GET returns an otherwise valid original body must reject
before saving the after snapshot. Stable same-principal restart with a new
service instance remains valid. Original result/digest/delivered ID and all
request identities, usage (including null) and reservations remain checked.

Move these three already-frozen counterexamples into normal Node CI. First
run the new tests against original PR57 `9d7fe98` without changing its driver;
then run the exact same tests on the author fix and PR58 combination. These
tests execute only source fragments and synthetic GETs, never a driver main,
model call, cancellation POST, host or browser. Existing evidence remains.

One 1–2 hour review/integration outcome; no new card or product slice. The
implementing session does not independently approve its own PR58 source;
DSH's review covers that unchanged source, while this session independently
reviews DSH's two-file final-read repair. Current-head CI remains mandatory.
