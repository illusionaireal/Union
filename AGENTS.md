# UNION / ai-union repository instructions


## 每轮先核对（2026-11-08 审查处置）

1. 先读本文件与 [当前交接](docs/reviews/2026-11-08-review-disposition.md)，核对真实 HEAD、工作区已有改动。
2. 日常状态、负责人、依赖、WIP 只读在线 Kanban；读取失败不退回本地认领。
3. 本地 project.json 保存长期路线、历史状态与交付证据；不据此占用在线卡。
4. 写前用实际 user.id 和最新 version；HTTP 200 才确认；409/丢失响应先读回。
5. 只续做自己负责的卡；已开工 blocked 仍占 WIP，不清空 owner 隐藏责任。
6. 行为代码先冻结契约、观察真实 RED，再最小 GREEN；不得撤掉正常代码制造 RED。
7. S03 下一出口是自动执行与真实有界验收；暂停扩展纯手工记账 UI。
8. 开发者在独立 checkout 的任务分支交付 PR；协调者审阅并合入集成分支。
9. npm check、Python 全量及受影响检查通过；权限/金额/身份还需另一工程角色复核。
10. 只提交自己的路径/片段；不得 reset/clean/stash 或动他人索引、冲突副本。
11. 不把私钥、邀请、API key、数据库、私有部署地址写入 Git 或留言。
12. 实施者 actor 与在线成员 ID 分别记录；不把开发代理称作产品 AU 成员。
13. 证据归入每个 U 卡目录并索引；旧证据和失败历史保留。
14. 只有本卡完整验收通过才 done；文档、受控、真实、持续分别陈述。
15. 用户已授权协调者 NAS 部署与合并；真实业务/迁移等其他边界按实际授权核对。

## Current authority: Main Chapter V1 (2026-11-05)

- The user explicitly instructed: “现在你使用Main中的Chapter V1 重新构建”. The authoritative project charter is `docs/UNION_CHARTER_v1.0.md`, copied byte-for-byte from main commit `b2a30f3af4ad69a679c4860468d744dd285a0098`; adoption, hash, authority and scope are in `docs/CHARTER_ADOPTION.md`. It supersedes conflicting older PRD, DESIGN, AGENTS and rewrite assumptions. Do not ask again whether to use this source.
- Use `AI-UNION / AU` for the organization concept/instance; `ai-union` for the open-source, independently usable technical core; `AI-Union-Platform` for the optional private commercial platform using public core contracts. `CONTEXT.md` records these terms. The core must build, run and validate without private platform accounts, repository credentials or license services, and provide basic authentication, AU authorization and audit. This does not bypass the authorization of a chosen adapter, including modeld AU grants/revisions.
- Single-Agent AUs are valid. Do not impose a universal two-member minimum, industry roles, fixed hierarchy, channel or workflow. Existing two-member collaboration and novel-company three-chapter/mock-accounting scenarios remain specific benchmarks. AI and human members, Agent definitions, bindings, sessions and processes are distinct.
- The Project Charter, each runtime AU Charter, and developer AGENTS are different authority boundaries. AU governance uses its identifiable initial governing principal and effective rules; default creator binding must be trusted. `legacy_board` remains an implemented compatibility authority, not the only possible product governance. A display name, controller_ref, platform account, payment or host access does not grant AU authority.
- Follow the charter's 40 normative clauses and conditional applicability. The five-layer architecture, Outbox and leases are illustrative mechanisms, not mandated services or technologies. Composition, local recovery, continuous responsibility, low-impact authorized trials and evidence-based improvement remain requirements even where implementation is incomplete.

## Reading and delivery workflow

- Read README.md, PROJECT.md, docs/ai-union/STATUS.md, HANDOFF.md and docs/DEVELOPMENT.md for current entry points, then the adopted Charter, docs/PRD.md, docs/ARCHITECTURE.md and applicable docs/decisions ADRs. For rewrite work use specs/053-union-rewrite/plan.md, tasks.md, charter-traceability.md and s01-contract.md. Old planning is recoverable from Git and is not a parallel active baseline.
- Read docs/product-design.md and docs/FRONTEND.md before changing user-facing behavior. Keep the React/TypeScript/Vite workspace; do not recreate retired independent single-HTML demos/reports or their dedicated scripts. Historical evidence is not a current capability claim.
- Use PRD -> architecture and pre-code ADR -> vertical slices with AGENTS -> strict TDD. ADR-0004 owns the user-selected method; ADR-0005/0006 own the selected V1 engineering direction. Accepted design does not mean code, runtime governance or deployment has changed. Freeze the affected contract before behavior code.
- `TDD Route: strict` is the user's explicit instruction. Observe a meaningful failing behavior test, implement the minimum passing change, then refactor with regression coverage. Preserve already-correct behavior; never break working code to manufacture RED. Documentation/generated views use structural and consistency checks.
- Each slice delivers a user-observable result through its necessary UI, API, application, persistence and tests. Record requirement IDs, effective identity/version, transaction/side-effect/recovery, compatibility and evidence. S01 has three sequential internal steps; partial legacy work cannot close U-066 or claim V1 creation completed.
- Add local AGENTS only when actual code responsibility moves into that module. Do not prebuild empty packages or hypothetical ports. Fix contracts and file ownership before delegating independent work; shared transactions/schemas integrate sequentially. The coordinator alone mutates the ledger, online board integration and Git; development subagents are not product AU members.
- S01/U-066 now delivers controlled stable core identity, prepared V1 AU creation/reopen and legacy isolation on `rewrite/charter-v1`; evidence is in `evidence/056-s01-core-creation/`. `dev` remains the development mainline. Before continuing, check real branch/HEAD, upstream, task availability and existing edits. The next planned slice is S05/U-069; no implicit authority to execute future slices, activate autonomous business, migrate live data or deploy.

## Product and runtime invariants

- The core is independently usable; the platform is optional and cannot bypass core public contracts or prescribe an AU's business/structure. ai-union-corp is the concrete company building these products, not the definition of every AU. Preserve specs/006-novel-company as a separate benchmark.
- New V1 autonomous business requires a bound governing principal and effective authorization. Resource-holding, external commitment and sustained operation require the applicable final decision party, reserved matters and governance-unavailability succession/recovery/exit procedure. Unavailable capability is explicit; preparation does not claim activation.
- Positions/appointments or an explicitly equivalent small-AU binding carry duties and authority. Execution must link responsible Member, Work, Mandate and Agent Definition version. Failed or replaced sessions/processes do not erase work responsibility. Current scoped member identity is `(au_id, member_id)`; simultaneous cross-AU membership is not implemented and transfers need explicit handover.
- Validate current authorization/versions at the relevant action and result-acceptance boundaries. State adoption and execution intent must be atomic or equivalently reliably linked; do not claim a global cross-database/filesystem transaction. Unknown external results require original-request lookup/reconciliation, not silent replay. Local cancellation does not prove remote cancellation.
- Recover locally where possible; an unknown job must not block unrelated work by default. Waits have a durable object, wake condition and responsible subject; long jobs retain a new-input path. Supervision is outside the supervised execution and has limited authority; supervised agents cannot silently change/delete their own supervisory records.
- One fact has one logical writer. Migrate one use case at a time, rebind callers and retire its duplicate implementation. Keep original AU/member IDs, decisions, assets, reservations and unresolved executions; do not dual-write, dual-dispatch, auto-migrate on reads or create new AUs to conceal old history. New V1 prepared data must not be writable through legacy Engine/CLI/runner/tool paths.
- Chapter C-01–C-05 are tracked in S10/U-076: common external contract, separate governance/collaboration/deployment relations, revocation/offline boundaries, commitments/disputes and restructuring handover. Old U-028–U-031 are implementation/history references, not new requirement dependencies. Phasing does not turn a fixed task tree into the product definition.
- Low-impact changes may be tried within existing authorization with version/check/withdrawal evidence. Permission to try and proven improvement are different. Implementation/evaluation duties must be distinguishable but need not create another Agent. Where independent judgment is required and unavailable, retain the candidate. Follow the Charter when updating management/SELF_IMPROVEMENT.md.
- Report human participation as remedial intervention, routine business labor, reserved governance, voluntary participation or uncertain. Keep outcomes, total costs, failures and uncertainty visible; do not equate agent dialogue, fixtures or document editing with real autonomous improvement.

## Task source and collaboration

- `management/project.json` is the long-term roadmap, historical milestone and delivery evidence source; hosted Kanban alone owns current operational status, ownership, dependencies and WIP. Read management/README.md and TASKS.md when selecting work. Use the unified online board adapter for operational writes; the coordinator explicitly records delivery milestones locally, then runs npm run management:render and npm run check:management. Local status/leases/WIP remain historical, never an operational fallback. Do not hand-edit generated PROJECT.md blocks or TASKS.md or create another ledger.
- The user selected hosted Kanban and required removal of old-engineering requirements. Old online cards #1–#18 are archived; #19–#30 map one-to-one to the 12 V1 slices/U-065–U-076. Use only active cards and V1 dependencies. Follow management/KANBAN.md: use actual user.id/current version, confirm HTTP 200 on claim, inspect 409/uncertain writes before retrying and publish real branch/evidence. Keep local checks offline; no automatic two-way sync or hidden status inference. Online card prose does not expand authorization.
- Started blocked work still consumes WIP. Preserve existing task histories/owners/blockers; adjust capacity only with an explicit recorded reason, never by hiding blocked work in backlog. Completion records distinguish documentation, controlled, real and sustained evidence; real goals do not close because a planning or engineering subtask passed.

## Verification, privacy and history

- Follow docs/FORMAL_DEVELOPMENT.md: engineering, real integration, user acceptance, release readiness and sustained operation are separate gates. Phase changes and historical checks do not authorize spending/deployment or upgrade evidence. Prefer installable, maintainable real workflows over demonstrations.
- Run npm run check and Python `-m unittest discover -v` using the pinned project toolchain; Windows uses `.venv\Scripts\python.exe` with PYTHONUTF8=1 and PYTHONIOENCODING=utf-8. npm checks management/history/action-safety/frontend, not real organization operation or PostgreSQL/Temporal. Use relevant actual-browser, model-service and release tests when the changed slice needs them.
- Authority, persistence, handoff, wakeup, accounting and executor changes require meaningful behavioral tests. Money/authorization/identity migration require another engineering role's review before adoption; tests alone do not suffice. Real models, tools, profiles, hosts and observation windows need their own bounded evidence and actual resource authorization.
- Read specs/019-au-core-contract/spec.md and migration.md, plus docs/AU_CAPABILITY_AUDIT.md before widening existing observation or authority surfaces. Existing describe_au_v1/controller metadata are limited implementation evidence; do not infer real cross-AU execution, delegated host access or V1 conformance. Reuse existing Harness loops and 048 model-service separation.
- Preserve PLAN/OPS/ENG/U identifiers, baseline/input bytes and historical test/operation evidence. STATUS/HANDOFF entries are dated history; current claims use the actual ledger and evidence. Legacy platform gates are not automatic prerequisites for separately authorized organization work.
- Never commit credentials, board keys, databases, customer data or private executor logs. Keep real deployment addresses/SSH/private paths in host-local configuration; repository examples use placeholders. See docs/DEPLOYMENT_PRIVACY.md. Protect Kanban invitations/keys and do not print them.
- Amounts use explicit currency and integer minor units for new accounting; unknown results retain reservations. Keep mock/testnet/real funds distinct. Choosing the open-source direction does not choose a license or authorize repository visibility changes, model spending, purchases, signing, production migration or deployment.
- Preserve task-preexisting dirty/untracked work. Stage only this task's files or owned hunks; do not reset, clean, stash, broadly add or commit another person's changes. Reuse the current checkout; do not create a worktree unless explicit project/user needs require it.
