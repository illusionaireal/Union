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
Current-head CI must verify that repair; the first failure remains recorded.

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

Independent duty review on 2026-11-09: [current findings and reproducible probes](independent-review/README.md). PR50 remains unapproved pending the truncated-output authority repair; 17 browser assertions passed, with a separate fixture cleanup fault.
