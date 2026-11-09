# U-086 / #40: verify the reopened original result body

2026-11-09; single codex-home duty implementation. Base PR69 at `7f02d38c`,
branch `codex/u086-reopened-download`; online scope comment287. DSH retains
ownership and the real parent exits remain incomplete. U106 was already adopted.
The authenticated engineering board member is codex-home /
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`; the implementation actor is this single
Codex duty session, not a product AU member.

The download driver previously checked complete persisted metadata after a
restart, but did not read the body. A matching snapshot could pass even when
the result endpoint denied access or returned a missing/corrupt body. Following
the [frozen contract](contract.md), the actual driver now GETs the original
AU/Work/result and validates current principal/service, complete metadata,
UTF-8 byte count and content digest. Evidence contains hashes and IDs, not the
body. The product, its authorization, transactions and model loop are unchanged.

- Actual original restart tail: 1 normal control passed, 14 new negatives
  failed before the repair; all 15 pass afterwards. Initial extraction-marker
  error is kept separately and is not a behavioral RED.
- Actual Chrome/Core HTTP/SQLite: the original tail passed its normal control
  but failed to reject all 10 body-response/access faults (zero result GETs).
  The candidate passes all 11 scenarios with exactly one original result GET
  per scenario. Responses are fault-injected after a real service restart;
  persisted data is unchanged. Each run prepares its result through two fake
  model turns; observations send zero business writes or real model requests.
- Six existing Node controls initially failed because their mock fetch only
  understood Work metadata. The two affected fixtures now also provide the
  real result DTO, digest and UTF-8 bytes. Their original identity/unknown
  reservation/usage/reordering assertions remain. All 286 related tests pass.
- Full checks and source/log hashes are in [validation.json](validation.json).

Reproduce with `node --test tests/exit22*.test.ts` and
`node evidence/U-086/reopened-download/browser.cjs`; set UNION_PYTHON to the
pinned interpreter and UNION_CHROMIUM_PATH to an installed Chrome. The browser
probe accepts UNION_EXIT22_DRIVER_SOURCE only to run the exact historical tail
for RED. It never runs either real-model driver's main.

Independent engineering review and this candidate's current-head CI remain
required. PR67/68/69's pending review is not supplied by this implementation
session. No real inference, deployment, migration or historical rewrite; the
20 pre-existing files, ordinary HEAD/index and dirty vendor remain preserved.

Final local checks: npm 295 Node / 363 frontend / 37 management, typecheck and
build passed; Python 808 tests / 10 skips / 0 failures
(509.106s) passed with pinned Bun 1.4.2. The initial npm launcher path
error is retained separately. No failed run was relabeled as successful.

During this implementation, PR69 received non-implementing review 5828308018
and all 35 exact-head checks passed. It was adopted as `57035fbe48b3845a811de2b94aa55c49af989704`,
with the same tree as its reviewed `7f02d38c`. This increment is based on that
actual integration; the earlier pending-review statements above describe the
initial implementation point. This new read still requires its own independent
review and current-head CI.
