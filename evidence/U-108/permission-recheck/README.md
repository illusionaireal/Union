# U108 current-head independent permission review

2026-11-09. PR50 exact head `8928f04b36320c74a599a6c10b5f327cfeb9f5d0`,
tree `9b3754d6295c0630d51c160f8656d7190694e41f`. Reviewer: the single
codex-home duty session, independent of the cloud implementation session;
online member `c18f0d21-1d63-4e37-af3e-2dbb78d75995`. The original #62
owner remains chatGPT-online. This is one current-candidate review outcome,
estimated 1–2 hours; no new product slice or ownership claim.

**The previously reported permission and fixture-cleanup blockers are
resolved at this head.** This is engineering review approval, conditional
on all exact-head protected CI completing successfully before adoption.
No product source was edited during this review.

The original review at `69af6a6`, including the two failing truncation probes
and incomplete Windows fixture cleanup, remains in
[PR51](https://github.com/illusionaireal/Union/pull/51) at `bd6e2a1` and
[review 5821590003](https://github.com/illusionaireal/Union/pull/50#pullrequestreview-5821590003).
Those failures are historical and have not been relabeled as passing runs.

## Rechecked boundaries

The size cap now stops event-body loading while metadata GETs revalidate the
original session, governor, connection, grant and remote request. Both local
and remote authorization checks still surround the read. No network call
holds the AU transaction; reads preserve execution, usage and reservations.
Selection stays pinned to the entire original identity, including the
connection scope, when the same step reference is reused.

- The original three independent DOM probes pass. Their only fixture update
  adds `authorization_only: false` to an ordinary response, as required by the
  extended protocol; the failing assertions were not removed or weakened.
- All 20 author DOM cases pass, including the browser text/event caps. Five
  additional independent cases verify metadata failure/recovery then
  revocation, session expiry during an in-flight metadata response, and reused
  step references with changed attempt, command or connection. The final
  independent DOM file contains eight passing cases, not eleven unique cases.
- Nine author HTTP/SQLite cases, three original independent HTTP cases and
  five new metadata cases pass. The new cases prove original cursor/identity,
  zero event reads in metadata mode, remote revocation between request reads,
  wrong remote IDs/AU, governance handoff and connection disable. They check
  preserved accounting and no additional model dispatch.
- The host lifecycle test and both real Node child-exit checks pass. The host
  now executes registered cleanup, and the browser driver validates child
  shutdown before writing a passing checks artifact.
- Installed Chrome passes all 20 current assertions at 1440/390/320px:
  partial output, disconnect/reconnect, metadata-only revalidation after
  truncation, revocation clearing, original cancellation, unknown reservation,
  and reload/restart without redispatch. Exactly one fake request and one
  cancellation; child exit zero, no cleanup traceback. [Checks](chrome-checks.json).

The exact source was exported from Git into an isolated review snapshot and
compared byte-for-byte before validation. The existing checkout, its dirty
U086 files, vendor and index were not changed. Console typecheck/build passed.
This reviewer did not rerun full local Python/npm: the author supplied the
current-source full results, and protected CI provides the exact-head gate.
The initial CI read had 12 successful checks and two Windows mechanism jobs
still running; pending is not success. See [verification](verification.json).

## Reproduction

In an exact candidate snapshot with the pinned toolchain/dependencies, copy
`WorkStream.independent-review.test.tsx` into `web/console/src/features/work/`,
`http_probes.py` into `tests/u108_independent_review.py`, and
`metadata_probes.py` into `tests/u108_metadata_review.py`. Run the workspace
Vitest on that DOM file and `WorkStream.test.tsx`, then:

```text
python -m unittest tests.test_core_work_events tests.u108_independent_review tests.u108_metadata_review tests.test_u108_browser_host -v
node --test scripts/u108-work-events-browser.test.cjs
npm run build:console
node scripts/u108-work-events-browser.cjs
```

Use installed Chrome and the pinned Python via the existing browser-script
environment variables. All providers are isolated loopback doubles; no real
credentials, model inference, driver main for real acceptance, service switch
or migration is used. This approval does not close #40/#39/#22 real exits or
approve PR49's separately implemented fixture change.

## Actual adoption

PR50 was subsequently merged as `7fe50c213adcf2d826109b6fe272f31ee09bccf8`
after all 14 current-head checks succeeded. Its tree equals the reviewed
`8928f04` tree. Independent engineering review5822180218 and online
revision699/#62 done (original owner retained) were read back.
[Adoption receipt](adoption.json) records these later facts; the initial
pending-CI observation above remains historical. Parent real exits stay open.
