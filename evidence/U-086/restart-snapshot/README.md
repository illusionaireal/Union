# Core snapshots and original requests across restart

The single codex-home duty implementer fixes the remaining offline snapshot
gap from #40 comments 242/248. DSH remains the owner; scope/estimate (2–4h)
was recorded in comment249 after a fresh board read. This candidate requires
another engineering role's review and current-head CI before adoption.

Both existing drivers previously saved `/api/snapshot`'s unsupported legacy
error as their before-snapshot. Their restart checks could also accept changed
requests or usage. The new shared helper reads the fixed original AU through
Core, validates the authenticated session and Work, and compares every original
step identity, connection, status, reason, usage and budget across restart.
The download driver's original result/digest/delivery checks remain in place.

Normal restart may replace service_instance, but each read must remain within
one current session and preserve the original principal/AU/Work. HTTP failures,
identity substitution, added/deleted requests and changed reservations fail.
`restart-request-comparison.json` reports persisted request-identity count and
per-request usage. Missing usage remains null even for a completed request;
transport dispatch count is explicitly unknown. The comparison cannot detect
replay under the same external ID and does not claim exactly-once transport.

## Validation and retained failures

- Original author `7493451`: 40 new tests, **3 pass / 37 fail**. These execute
  the unchanged snapshot/restart sections with synthetic fetch responses;
  no driver main or real inference runs. See the frozen [contract](contract.md).
- The expanded suite and prior output/download tests pass **100/100**; npm
  runs these plus 9 existing Node tests. Two additional completed-with-null-usage
  controls first failed on the initial candidate and then passed after removing
  its overstrict known-usage assumption. No unknown usage is converted to zero.
- [Actual Chrome/HTTP/SQLite probe](browser.cjs): two explicit fake turns via
  the existing automatic loop; Console stop/reopen preserves both requests and
  budget. Service-instance replacement succeeds; HTTP403 and wrong Work fail.
  The probe performs only GETs, checks fake-call count remains 2 and propagates
  fixture cleanup failure. Real model calls: **0**.
- npm check: **363 frontend / 109 Node / 37 management**, types and build pass.
- Original download probes: **11/11**. Their extraction stops before the new
  separately tested request comparison. An initial positive-control failure
  was a missing `delivered_result_id` in the review fixture, not a product RED;
  the corrected fixture retains all negative original-result tests.
- Full Python outcome and exact source/log hashes are in [validation.json](validation.json).

Existing files in evidence139, including the invalid historical before snapshot,
are unchanged. A new snapshot cannot retroactively supply that run's before
state. Its missing original-output file, page-visible output and same-command
replay/dispatch evidence still require original-run evidence from the owner.
#22/#39/#40 real exits remain open. No deployment, migration or additional model
spending occurred. The regular checkout/index and all pre-existing dirty files
were preserved; only this branch's named files were staged in a separate index.
