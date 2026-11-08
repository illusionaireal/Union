# Scheduled review of prolonged blockers

2026-11-08. The user explicitly requires the coordinator to intervene when work
remains blocked. A board fingerprint alone cannot wake a coordinator after time
passes without another edit. The existing five-minute poll and single writer
remain; this change adds a bounded review signal, not task ownership or a lease.

- From a fresh successful online board only, identify progress/review/blocked
  cards whose last online update is at least four hours old. The period may be
  configured with a positive integer `blocked_review_seconds` (minimum 300).
- Include card ID, original owner/status, online update time and elapsed review
  period in the observation. One unchanged period is acknowledged once; crossing
  the next period produces another review signal. No inference on every poll.
- Completed/archived cards do not trigger. Missing or invalid/naive timestamps
  cannot establish elapsed time. A failed board read cannot reuse stale ages.
- The coordinator diagnoses, fixes, resolves decisions or splits independently
  actionable work, retaining original ownership and uncompleted acceptance.
  An attention signal itself neither closes work nor authorizes spending.
- Preserve failure cursors, partial-source independence and the existing writer
  lock. Verify the time-boundary signal, deduplication, closed cards and failures
  offline before enabling the same reviewed source on the host.
