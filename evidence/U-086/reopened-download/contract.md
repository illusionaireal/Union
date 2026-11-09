# U-086: read the original delivered body after restart

2026-11-09; implementation actor: the single codex-home duty session. Candidate
base `7f02d38cd892b6d75bcc41437dbb5afe3377f131` (PR69). #40 remains DSH-owned.
Scope: one 1–2h acceptance repair, including verification; no separate product
slice. PRD F05/F11/N03 and the existing S03 original-result contract apply.

The download driver currently proves that result metadata survived restart,
but never reads the reopened result body. An unchanged digest in a snapshot
cannot prove that the body remains available or unmodified.

Before claiming download/reopen success, use only GET to read the original
`organization_id/work_id/result_id` under the original principal. Check the
current Core session before and after the result GET; both must identify the
same current service and original principal. A restarted service may have a
new instance; a change during this read is rejected. Require HTTP200 and
`core.work.v1`, the original AU/Work, and the complete original adopted result
metadata. Hash the returned UTF-8 body and check its byte length against the
original digest/bytes. No stale body fallback, replay, re-adoption or model call.
Only hashes, byte counts, IDs and scope enter the public evidence, never a body
or credential. Preserve all previous request/budget/result comparisons.

RED: execute the real driver restart block with matching snapshots while the
body read is missing, denied, corrupted or substituted. The old block must
incorrectly pass; successful original-body and Unicode cases are controls.
GREEN: minimal read-only helper and driver call; Node fault cases plus actual
Chrome/Core HTTP/SQLite restart, including unchanged metadata with a corrupted
or denied body response. Full npm/Python and current-head CI remain required.

This changes no product authorization, schema, transaction, timeout or
supervision. Controlled fake calls do not establish real business acceptance.
PR67/68/69 and this increment still need a non-implementing engineering role;
the implementation session does not self-approve. No real inference, NAS
service switch, migration, owner change or historical evidence replacement.
