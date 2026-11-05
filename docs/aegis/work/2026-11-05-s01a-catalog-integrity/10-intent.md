# S01a implementation checkpoint

This is an advisory Aegis work record. Current task state remains solely in
`management/project.json` (U-066); it is not another task ledger.

- Request: implement S01a, independently review it, verify, commit only this
  session's changes and push `rewrite/charter-v1`.
- Parent: `specs/053-union-rewrite/plan.md`, `tasks.md`, and `s01-contract.md`
  T01–T04. S01b/S01c and full U-066 completion are outside this checkpoint.
- Authority read: root AGENTS and latest HANDOFF; README, PROJECT, STATUS,
  DEVELOPMENT; adopted Main Charter V1 and adoption record; PRD, ARCHITECTURE,
  ADR-0004/0005/0006, CONTEXT, 053 AGENTS and charter traceability; management
  README/KANBAN/TASKS; product-design, FRONTEND and FORMAL_DEVELOPMENT.
- Charter source remains `b2a30f3af4ad69a679c4860468d744dd285a0098`.
- Requirements: F01/F03/F09/F11/P15/F17; D-01, A-01/A-04, R-01/R-02, X-02(a).

## TaskStartSnapshot

Root: `D:/Project/Union`. Branch/upstream: `rewrite/charter-v1` /
`origin/rewrite/charter-v1`. HEAD and freshly read remote branch:
`36ec591458cde470771326335bb281eedf159321`; divergence 0/0. No staged files or
merge/rebase/cherry-pick/revert in progress. Existing second worktree belongs
to `codex/model-access-0-5`; reuse this checkout.

Pre-existing tracked edits: `.gitignore`, root `AGENTS.md`,
`management/README.md`, `package.json`, `scripts/project-management.mjs`, and
the modeld OpenCode submodule. Existing untracked runtime helpers, management
tools/tests, historical evidence/specs, conflict documents, scripts and site
assets belong to earlier work. Preserve all of them; they are not delivered
by this task. Intake hashes/status are retained in the session for comparison.

## Execution boundary

Change Necessity: **code-change**. Console currently resolves catalog folders
without checking the stored AU identity; startup and shutdown then write to
that database. Documentation cannot enforce the boundary. Repair registered
AU resolution once and route interactive/lifecycle/discovery consumers through
it, before recovery or pause writes. Preserve existing create/receipt ordering.

TDD Route: **strict**, explicitly required by the user and AGENTS. First run
the existing creation/unknown tests; then observe the new wrong-AU mapping
test fail on the unchanged implementation, implement the minimum correction,
and refactor with the valid path and T01–T04 regression coverage intact.

Complexity/owner fit: Console mixes transport, catalog and jobs; Engine is
already large. Keep the repair at the catalog resolution boundary, extracting
a cohesive read-only persistence adapter if needed. Do not introduce V1
creation, schema migration, generic ports, or another state writer. New module
instructions accompany only responsibility actually moved there.

ArchitectureReviewRequired: existing ADR-0005/0006 and the frozen S01 contract
cover this change; no new architecture decision is planned. Independent
identity/persistence review is required before adoption.

Preserve original AU/member IDs, creation payload/receipt bytes, idempotency,
unknown allocations, controller_ref versions, company behavior and distinct
Console/Engine resource contracts. No live AU migration, model use or deployment.

Verification: first RED and focused GREEN, related Console/HTTP/identity/AU/
mechanism tests, fixed Node 24.19.0 `npm run check`, UTF-8 Python 3.13.14 full
unittest discovery, actual workspace browser regression, independent review,
candidate-only management checks, scoped Git diff and remote SHA readback.
