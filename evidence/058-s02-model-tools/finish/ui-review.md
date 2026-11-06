# S02 model UI independent review

2026-11-06. Reviewer: `/root/s02_feature_audit`. Working tree on `rewrite/charter-v1`, HEAD `d5802f8672df88db447e7e0bb86c2f1a5265ad18`. Advisory engineering review; no implementation, Git, ledger, board, live account or real model mutation/call.

## Findings

**No blocking implementation finding in the seven handed-off files.** The component/type evidence supports the reviewed UI behavior. Actual-browser layout, keyboard, and integration acceptance are still a separate coordinator-owned gate; this review does not claim those gates passed.

The implementer's handoff accurately records that the scope grew from five to seven files when the original stale-check recovery predicate was unified. The two added callers/owner changes are necessary to make the same recovery decision in the connection list and the current-state preview.

## Scope and authority

Inspected all seven current files under `web/console/src/features/models/`: `ModelRecords.tsx`, `types.ts`, `models.css`, `test-fixtures.tsx`, new `ModelsDiagnostics.test.tsx`, `model.ts`, and `ModelCommandForm.tsx`.

Basis: module `AGENTS.md`; S02 M08/M09 and the frozen error/usage continuation in `specs/053-union-rewrite/s02-contract.md`; current V1 sections of `docs/product-design.md` and `docs/FRONTEND.md`; `ui-finish/report.md`, `task-start.json`, and `verification-final.json`. Historical product descriptions were not treated as current acceptance evidence. The review used the existing code-review workflow with the applicable UI/UX recovery, readability and evidence rules.

## Specification and code review

- Diagnostic `next_step` stays beside its saving operation, overall check or individual attempt. `DiagnosticNextStep` renders React text rather than HTML; the UI neither reclassifies the error nor interprets it as proof of remote execution. Existing message, status, original request and explicit reconciliation paths remain visible.
- Each attempt independently renders token counts and `basis=result|events|unknown`, with the observation sequence in its details. The UI displays the received snapshot directly; it does not add cumulative and final values or combine two attempts. Missing new fields remain unknown, with no read-time migration. Missing currency keeps the monetary display unknown.
- `cancelled` is explicitly a local stop and is accompanied by the remote-cancellation/refund limitation. Existing unknown history, usage and occupied calls remain visible. There is no automatic replay or refund action.
- `hasBlockingModelCheck` in the existing `model.ts` is the sole shared UI predicate for current-revision, unstopped in-progress checks. Both `ConnectionRecords` and `ModelCommandForm.makePreview` call it. Old revisions and explicit local-stop requests no longer prevent an explicitly submitted new bounded check. Existing current permission, document authority, enabled connection, unknown-cost acceptance and two available calls still constrain the entry.
- A newly appearing current-revision check is rejected at preview without clearing the material input. Existing identity, AU version, request reference and server-authoritative submission handling remain intact.
- DTO additions are optional and fixture types retain responsibility/version metadata. No protocol selector or second backend state owner was introduced. The local security-note selector uses larger, wrapping text and higher contrast; numeric source contrast is not a browser layout result.

## Independent verification

Executed using the fixed project Node path from `web/console`:

```powershell
& '.union\tools\node.exe' 'node_modules\vitest\vitest.mjs' run src/features/models/Models.test.tsx src/features/models/ModelsIdentity.test.tsx src/features/models/ModelsRecovery.test.tsx src/features/models/ModelsDiagnostics.test.tsx
& '.union\tools\node.exe' 'node_modules\typescript\bin\tsc' --noEmit
```

- Components: 4 files, **51 passing**, exit 0. Vitest duration 7.69 s; subprocess elapsed 8.487 s. Includes the original 34 cases and 17 new cases; the six eligibility cases exercise both disabled controls and complete explicit submission paths.
- Types: **passed**, exit 0, subprocess elapsed 5.617 s.
- All seven source hashes were recorded before/after and were unchanged, matching the implementer's final handoff. Commands, hashes and outcomes: `ui-independent-review-checks.json`; complete output: `ui-independent-review-components.log` and `ui-independent-review-types.log`.
- Existing RED/GREEN records were reviewed as implementation history: diagnostic failures followed by 45 passing, eligibility list failures followed by the independent preview-condition failure, then final 51 passing. A failed intermediate run is not counted as passing evidence.

The checked tests cover diagnostic ownership and escaping, absence of new fields, partial event usage through local stop/revocation/interruption, per-attempt snapshot replacement, original-ID reconciliation without automatic POST, read-access loss clearing, previous revision and stop-request recovery, preserved reservations, and remaining permissions/capacity.

## Remaining evidence and assessment

`ui-finish/report.md` correctly states no new actual-browser run. `.union/s02-ui-browser/failure.json` records the earlier completed-result readability failure at 1440 px; its preceding successes do not establish the changed view now passes. Source color calculation and jsdom tests do not prove physical layout, keyboard focus, 320/390/1024/1440 behavior or the real HTTP/SDK UI journey.

**Ready for coordinator integration: Yes within this bounded code/component/type scope.** Coordinator still owns actual-browser and backend integration checks, final root verification, installation and separately authorized real-profile acceptance. This review is not U-072, M09/M10, S02 or release completion authority.
