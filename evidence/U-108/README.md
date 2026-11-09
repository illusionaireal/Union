# U-108: original Work output observation candidate

2026-11-09. Kanban #62, owner chatGPT-online; implementation actor is this
Codex cloud session. Baseline `a401d2ba3469b48b3125b749c57c21b756536bbf`.
Scope/6–8 hour estimate and successful v1→v2 claim are recorded on the card.
The [contract](contract.md) was frozen before behavior code. D-01/D-04,
A-01/A-03/A-04 and R-05/R-07/R-08 remain the applicable Charter boundaries.

## Change

Core `/tasks` can explicitly expand a saved automatic Work step, display its
own modeld text events, reconnect at the original cursor and use the existing
cancel control. The new GET binds the stored Work/attempt/step/command/model
request and original connection/grant versions; it does not accept another
request ID from the browser. It rechecks the current governor, enabled original
connection, current grant and modeld read authority around network reads.

The modeld durable journal remains the event owner. Local SQLite snapshots are
read-only; no model dispatch, grant creation, reservation settlement, adoption,
schema migration or alternate execution loop is added. Only text and supported
tool names are projected. Native/private arguments are omitted. Text is bounded
and held in component memory only. Current read permission is separate from
new-action eligibility; cancelled/unconfirmed remote calls remain unknown facts.

## Observed validation

- Unmodified baseline behavior: initial HTTP run was four assertion failures
  plus one missing-payload test error; adding the status assertion before field
  access gave **5 meaningful HTTP failures, zero errors**, all HTTP404. Original
  UI gave **2 DOM failures** because the observation control did not exist.
- Minimal implementation and expanded fault coverage: **8 HTTP/SQLite tests**
  pass, including in-flight text with reserved=1, exact read/restart, current
  role/connection/grant races, privacy, pagination, duplicates/conflicts and
  truncation. One intermediate negative-sequence fixture filtered out its own
  malformed event; it is retained as a fixture error, corrected by transporting
  the malformed page unchanged to the API validator.
- **14 DOM tests** pass: original scope, connection revision, session changed
  after GET, permission loss, delayed reply, disconnected-prefix/cursor recovery,
  pinned original selection and permission checks after terminal output.
- Standard `npm run check` passes: **357 frontend, 37 management, 9 action
  tests**, typecheck and build. The existing chunk-size warning remains.
- A separate actual Console/SQLite/loopback HTTP smoke run passes **15 checks**:
  partial output before cancel, one original fake dispatch, original cancel,
  unknown reservation and same-step restart. Its first invocation omitted the
  Core Origin header (HTTP403); that fixture invocation is not a product fault.
- Local Chrome launch failed because the executable was absent. Official
  Playwright full-Chrome and smaller headless-shell downloads both returned
  truncated/non-ZIP content. These failures are retained; **no local Chrome
  pass is claimed**. `u108-work-events-browser.cjs` and its disposable HTTP host
  are added to the existing browser CI job for actual Chrome verification.

Full Python passes: **800 tests, 5 skipped, 0 failures** (326.758 seconds).
The skipped real/modeld/release checks are not upgraded. Accurate-head CI/browser
results and independent engineering review are recorded separately as they complete. The implementation cannot approve its
own identity/permission boundary. This candidate is not yet adopted or complete.

### First accurate-head CI feedback

Head `8bcf5da` passed both Windows/Linux offline checks and the model-service
workflow. The browser job `128972730793` failed the existing U081 regression
with `overflow at 390px`; the new browser driver had not run yet. The long
original-request option imposed an intrinsic select width. A scoped CSS repair
bounds the selector and wraps displayed identities; no assertions were relaxed.
The U108 actual-browser script now also checks expanded output at 1440/390/320px.
That exact head `69af6a61e9f3f24182226239d242d26a912a94d1` subsequently passed
all three workflows (42560040005/42560040008/42560040010), including all 17
actual Chrome assertions at 1440/390/320px. The first failure remains recorded.

### Independent review and corrections

Independent engineering review [5821590003](https://github.com/illusionaireal/Union/pull/50#pullrequestreview-5821590003)
found that display truncation stopped permission checks and disabled manual
rechecking. Truncated private text survived a later 401/403. The review's
reproducible probes remain in [PR51](https://github.com/illusionaireal/Union/pull/51)
at `bd6e2a1`; they are not implementation approval. Its 8 HTTP, 3 independent
scope/race probes and 17 Chrome assertions passed, separately from the failing
permission cases. Review also found missing registered unittest cleanup and no
parent-side check of browser-host shutdown.

The correction separates body limits from current authority: at any cap the
browser only requests the same origin/cursor with `authorization_only=1`.
The server performs the same local/governor/connection/grant/request checks,
skips event-body loading, and returns no events. 401/403 clears the retained
body; a temporary failure permits another metadata-only query. Selection now
pins the entire original identity, including the original connection, so a
same-step_ref source replacement cannot be silently followed. The fixture runs
its registered cleanup, and the Node driver waits for a successful child exit
before writing a passing result.

Observed RED and intermediate fixture-assertion corrections are retained in
[review-fix-red.txt](review-fix-red.txt) and [cleanup-red.txt](cleanup-red.txt).
Current controlled checks: 9 actual HTTP/SQLite, 20 DOM (server truncation,
256Ki text/20k event caps, later 401/403, transient metadata failure/recovery,
and original identity), 1 actual host lifecycle, and 2 real child-exit checks
pass. `npm run check` passes 363 frontend / 37 management / 9 action tests,
typecheck and build. Current local Chrome still reports a missing executable;
no new local Chrome pass is claimed. The CI browser driver adds truncation ->
metadata-only recheck -> revoked-body clearing to the original flow, while
preserving one fake dispatch/cancellation and zero real model calls.

The correction needs accurate-head CI and another engineering role's recheck;
prior-head green checks do not approve this new source. Parent real exits remain
unchanged.

## Reproduction

```sh
.venv/bin/python -m unittest tests.test_core_work_events -v
npm run test --workspace @union/console -- --run src/features/work/WorkStream.test.tsx
.venv/bin/python -m unittest discover -v
npm run check
UNION_PYTHON=.venv/bin/python node scripts/u108-work-events-browser.cjs
```

All model calls here are explicit loopback doubles. The browser driver requires
one original fake request and one cancellation; it never connects a real profile.
The full-loop HTTP smoke likewise used one fake dispatch. Real inference, live
migration, key creation/rotation and business service switches are all **0**.
Parent #40/#22 and real #39 acceptance remain open; other owners are unchanged.

## 2026-11-09 current-head independent recheck

The single codex-home review session independently rechecked `8928f04`: prior
permission/cleanup blockers resolved, 28 unique DOM / 17 HTTP boundary cases,
host lifecycle / two child-exit checks and installed Chrome20 pass. Exact-head
CI remains the adoption gate; real parent exits remain open. Reproducible
probes and source/log hashes: [permission recheck](permission-recheck/README.md).
