# Original cancel GET and restart recovery

The single codex-home duty implementer continues #40 under scope comment251;
DSH retains ownership and history. Author/PR57 input is `9d7fe98` and the
integration baseline is `4aa020b`. This is a controlled acceptance-driver repair,
pending another engineering role's review and exact-head CI.

The previous driver accepted a cancel GET with a failed HTTP status or a
substituted actor/step, and never queried that cancel command after restart.
The driver now reads the original Work and receipt between authenticated Core
session checks, correlates the original step/attempt/command/model/connection,
and compares the complete receipt against the original POST before and after
restart. Public receipts do not have Work/attempt fields; their original step
must resolve within the fixed Work. Normal service-instance change on restart
is permitted. All evidence reads are GET-only.

Validation follows the [frozen contract](contract.md):

- Unmodified author source: 34 tests, **1 pass / 33 fail**. The successful
  original-receipt control passed; wrong HTTP/identity/status and missing
  post-restart receipt were meaningful failing counterexamples.
- Candidate: all **34/34** pass. Prior original-output, download and request
  snapshot tests also pass, **134/134** combined. The prior snapshot fixture
  isolates this new separately tested receipt gate; its snapshot tests remain.
- [Actual Chrome/Core HTTP/SQLite](browser.cjs): original cancel receipt survives
  stop/reopen, service changes, wrong Work/attempt/principal and HTTP403/substituted
  actor are rejected. One fake inference and one fake cancel; observations add
  zero POSTs. Fixture shutdown failure propagates to the result.
- Full checks, source hashes and private log hashes: [validation.json](validation.json).

The new before/after receipt files demonstrate local intent and durable delivery,
not remote cancellation or zero external redispatch. The existing request/usage/
budget comparison continues to preserve unknown occupancy. No real driver main,
new inference, service switch, migration or supervisor/config/lock mutation ran.
Evidence139 is unchanged; its missing historical before snapshot and output file
cannot be reconstructed by this change. Page-visible output, same-command replay
and actual transport counts remain separate real exits; #22/#39/#40 stay open.

The source was prepared from exact Git objects using a separate index in the
existing checkout. All pre-existing worktree files, vendor changes and the regular
index remain untouched. This implementation session does not self-approve.
