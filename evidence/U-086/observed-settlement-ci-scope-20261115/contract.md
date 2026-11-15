# U086 observed-settlement browser scope repair

Frozen before the test edit on 2026-11-15. Candidate 3a4fecb1c072d51d4748234191e390297c1a1a22.

The existing single-step Chrome fixture validates settlement/restart and original cancellation receipt recovery. It intentionally excludes the generic snapshot comparison because this older fixture omits usage; the separate Node and full-loop HTTP/browser suites own that contract. New inline comparison code must not silently widen the extracted fragment.

Preserve the actual unknown control, both released rejection controls, original GET, exact SQLite steps/budget across restart, no browser writes and one fake dispatch/cancel per scenario. Keep all production snapshot checks and unknown values unchanged. End the fragment before the new replay observation/comparison block and fail clearly if its marker is unavailable.

Observed RED: current-head GitHub job 132816944327 and a built, exact exported candidate in local Chrome both fail the unknown control with `explicit request usage, including null`; two released controls pass. The first local attempt lacked frontend build output and is retained as a setup failure, not behavioral RED.

One independently verifiable test-maintenance outcome, estimated 1–2 hours including validation. No product model calls, authority/accounting changes, shared implementation edits, deployment or migration. DSH retains #40 and real acceptance.
