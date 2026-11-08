# Prolonged blockers wake the coordinator again

2026-11-08. Implementer: the foreground deployment coordinator, separate from
the supervised scheduled worker. The user explicitly requested intervention for
long-blocked tasks. This follows the [pre-code contract](overdue-review-contract.md).

Previously, acknowledging an unchanged snapshot could leave a blocked card quiet
indefinitely. Fresh online progress/review/blocked cards now produce an attention
signal after four hours without an update, and again at the next four-hour period.
The normal poll remains five minutes. `blocked_review_seconds` may change the
review period (integer, at least 300 seconds); it is not a task or model timeout.

The signal carries the original ID, owner, status and online update time. It does
not claim, release, close or edit a card. Done/archived cards and timestamps that
cannot establish an age are excluded. A failed board read never ages cached cards
into current facts. Existing partial-source handling and the single writer lock
remain intact. The worker must diagnose and advance the flagged work, retaining
ownership/history and respecting actual resource authorization.

Two new assertions fail on the unchanged watcher: elapsed time did not wake a
review, and current overdue cards were absent. After the small observation change,
all 17 watcher tests pass, including period deduplication and failed-board behavior.
Log digests and delivery verification are in [the record](overdue-verification.json).
Only a verified copy of this source is adopted on the host, with its previous copy
retained. No new scheduled task, extra model worker, credential or AU authority is
created. This is coordinator maintenance, not autonomous product acceptance.
