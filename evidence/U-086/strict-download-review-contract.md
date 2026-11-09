# Strict download candidate: independent review contract

2026-11-09. Reviewer: the single codex-home duty session, online member
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`. Author DSH retains #40 and its
driver edits. Review input is `bdbbb9b` and current author head
`1d9ed8e9ddcaed949d38218186ede28d216dfb8f`; integration is `902b429`.
Kanban comment 195 records the 1–2 hour review scope, without a new claim.

This contract is frozen before adding the review probes. It applies the
existing #39/#40 and U106 original-result identity and recovery requirements;
it does not introduce a new runtime protocol or alter a shared transaction.

- Accept the original successful download whose AU, Work, result ID, title and
  UTF-8 content digest match the previously read result. Keep a passing control.
- Reject the previously reported error body, null result and another result;
  also reject changed content or title. A corrected assertion earns only this
  specific validation, without retroactively validating evidence/128.
- A matching result ID/content/title must not substitute for the response's
  original AU and Work scope or a successful HTTP response.
- After restart, require the same delivered Work and adopted original result;
  another adopted result cannot establish survival of the original one.
- Inspect saved evidence/129 for request count, usage, tool results, original
  IDs, digest and successful same-run before/after observations. Count recorded
  requests separately from remotely verified dispatches or billing.

Extract only the exact assertion blocks from Git, execute with synthetic inputs
and an in-memory HTTP response, and distinguish failed behavior expectations
from parser/runtime errors. Never import or execute the driver's main, host,
browser, model transport or credentials. No source repair is made in this review.
Record missing facts as unproven; do not request a new real run to fill them.

Product, schemas, historical evidence and live task owners stay unchanged. The
host connection fix from this implementation session still needs another
engineering role's review before adoption; this review cannot approve it.
