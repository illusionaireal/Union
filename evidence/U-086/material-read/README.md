# U-086 / #40: verify the material read before adopting its result

2026-11-10. Single codex-home duty implementation; online member
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`, scope comment290. DSH remains owner.
Base PR70 `2ba812f8018b23f7e6f2ba7d0d28c67be28b97a4`; branch
`codex/u086-material-read-evidence`. U106/#60 was already adopted.

The download acceptance driver could accept a result containing the synthetic
nonce without any persisted `read_document` receipt. The pre-delivery gate now
requires the original Work's unique material receipt, matching path, SHA256 and
UTF-8 bytes, the original candidate's source link, and a persisted attempt with
an executed automatic model request. The existing successful page-delivery
artifact includes only the material reference/hash summary, never its body.

The [contract](contract.md) was frozen before the behavioral change. The actual
old driver gate passed its normal control and incorrectly accepted all ten
Node counterexamples. It also passed one genuine Chrome/Core HTTP/SQLite
control and incorrectly accepted nine response faults. The final gate passes
all 11 Node cases and all ten Chrome cases. Observations perform no business
writes; each disposable browser host prepares exactly two fake model turns.

Failures are retained separately in [validation](validation.json):

- The first implementation read legacy `attempt_ids`, incorrectly rejecting
  the genuine HTTP normal control. Actual S03 attempts live in `work.attempts`;
  the minimal correction and a Node control with empty `attempt_ids` preserve
  that distinction. No product data or authorization was changed.
- Two related Node checks failed because their mock overwrote `crypto`; the
  fixture was corrected. This was not a product RED or a weakened assertion.
- The earlier page-delivery fixture now supplies its actual material expectation
  (`nested/a.md`, known UTF-8 bytes) to the same driver gate. Both actual Core
  controls still succeed; missing controls still cause zero writes. Those two
  Chrome cases pass, as do PR70's eleven original reopened-body cases.

The receipt/source link is bounded evidence of a recorded read. It does not
independently prove the second model's complete input, real billing or business
quality. #22/#39/#40 real exits, prior uncertain evidence, and #61's migration
decision remain unchanged. No new real inference, grants, deployment, migration,
supervision/config/lock changes, or independent self-approval.

Reproduce with `node --test tests/exit22*.test.ts` and
`node evidence/U-086/material-read/browser.cjs`, using the pinned Python and
installed Chrome environment variables. The latter accepts
`UNION_EXIT22_DRIVER_SOURCE` solely to probe the exact historical gate; it never
executes a real-model driver's main. The existing CI includes this probe without
removing checks or changing timeouts. Full-check results and source/log hashes
are recorded in validation.json. Another engineering role must review this
exact candidate, and its current-head CI must pass before adoption.

Final local checks: Python 808 tests / 10 skips / 0 failures or errors
(516.201s), npm 306 Node / 363 frontend / 37 management, typecheck and build
passed. All 297 related driver checks passed on the final LF source bytes;
23 combined Chrome cases passed. The earlier 808-test SDK environment failure
(518.656s) is retained. Across the dedicated browser runs, 14 fake model calls
and zero real calls were made; full-suite fake integrations are separate.
