# UNION / ai-union repository instructions

## Active direction and source of truth

- Product boundary confirmed 2026-10-20: ai-union is the AI-centered collective that autonomously organizes, acts, and adapts its members, positions, processes, and capabilities around a shared goal. ai-union-platform (also called UNION platform) provides creation, hosting, observation, integration, and other shared services without prescribing an organization's business, structure, or operating methods. The organization decides how to develop and achieve its goal within its charter, authorization, and resources; an ai-union may itself build and operate the platform. The exact approved wording is in `docs/ai-union/DESIGN.md`, section "2026-10-20：已确认的作用和边界".
- Apply this boundary throughout the organization lifecycle, not only during bootstrap. Business capabilities follow each organization's goal; coding is not a universal prerequisite. Do not turn current tool limitations into the product definition or infer a requirement that every organization must run without the platform or obtain every capability through it. Keep the organization runtime and the platform product conceptually distinct.
- Independent single-HTML demos/reports and their dedicated source/build/deploy/check scripts were retired by the user. Maintain the React workspace; preserve historical evidence and Git history, but do not recreate those artifacts.
- Use `dev` as the ongoing development mainline (user decision 2026-10-15). Current first experience is `specs/006-novel-company`: real model execution, three same-book chapters/cycles, host-owned mock platform/accounting, controlled negative feedback, and human quality review. Do not require real external publishing for this first experiment; that remains a later milestone.

- Read README.md, docs/ai-union/STATUS.md, HANDOFF.md, and docs/DEVELOPMENT.md first. Read docs/PRD.md and docs/product-design.md before user-facing work; current frontend is specs/005-frontend-engineering, continuing specs/004-organization-console with specs/003-runtime-dashboard as its observation module. Read docs/FRONTEND.md for React/TypeScript/Vite setup, architecture and validation. Keep scope, flows, design and acceptance aligned with the latest user decisions. Read specs/001-org-bootstrap for the implemented runtime. Treat docs/ai-union/DEVELOPMENT.md as the original development brief, not a current completion report. Use docs/ai-union/DESIGN.md for product and governance context and ADR-0002 for the transition from the original platform plan.
- The user has confirmed the ai-union direction: goal-driven organization formation, real collaboration, persistent state, and subsequent action. Reuse existing Agent execution loops; prioritize the organization loop.
- Keep ai-union and the UNION platform as separate product and planning tracks. Do not inherit the legacy payment/platform task order for the organization prototype.
- Treat confirmed product decisions as requirements. Concrete schemas, modules, libraries and deployment choices remain engineering proposals until selected and recorded.
- Use lightweight Spec -> Plan -> Tasks -> Implement, TDD for critical deterministic mechanisms, and real Agent evaluations for organizational capability. Do not stop at a plan when implementation is requested and feasible.

## Product and governance

- Do not hard-code content-industry roles, member counts beyond the two-member minimum, audiences, channels, or production workflows. These emerge within configured resources.
- The board retains ultimate control. Governance boundaries belong to the versioned runtime charter and may be amended through the currently effective procedure. Routine operations are autonomous within effective authorization.
- Runtime charters are distinct from developer instructions or a Spec Kit development constitution. Runtime charter changes do not grant host access or permission to rewrite the runtime.
- Positions drive duties, permissions and context. Keep member identity separate from execution sessions; preserve organizational knowledge, artifacts and responsibility across handoffs.
- Human-free is descriptive, not a zero-human requirement. Report human participation, actual outcomes, costs and uncertainty honestly.
- Distinguish implementation completion, a real-model prototype run, and the first release's real delivery/feedback/next-action acceptance. Mock outputs and role dialogue do not establish these outcomes.

## Historical assets and validation

- Preserve PLAN/OPS/ENG identifiers and docs/baseline snapshots. Record new execution status in docs/ai-union/STATUS.md and iteration artifacts; do not silently close or rewrite old task history.
- The legacy PLAN-001–006/M0 gate applies to the original platform scope and production adoption of that work. It is not a prerequisite for the separately authorized ai-union prototype development. Preparing code does not complete legacy ENG tasks.
- Keep mock, testnet and real funds distinct. Existing documentation and the offline spike do not enable real payments, marketing, model spending, signing or external deployment. Use actual configured permissions and explicit resource limits for real runs; carry forward existing user authorization.
- Amounts use integer minor units with explicit currency. Unknown external results retain reservations and require lookup in the existing action-safety implementation.
- Money and authorization changes require another engineering role's review before adoption. Tests alone do not satisfy that review.
- Run npm run check before proposing changes. It checks historical plan integrity, the offline action-safety tests, and frontend type/interaction/build checks; do not present it as organization-loop or PostgreSQL/Temporal validation.
- Do not change repository visibility or choose an open-source license without an explicit project decision. Never commit credentials or customer data.

## Current runtime engineering

- Bind acting identities in the host, validate current authority and versions, and submit state/decisions/dispatch records transactionally.
- Unknown external execution is a reconciliation condition. Do not silently retry it.
- Test changes to authority, persistence, handoff, wakeups, accounting and executor protocols with meaningful behavioral tests.
- Run `python3 -m unittest discover -v` in addition to `npm run check`. CLI operation is `python3 -m ai_union` from the checkout.
- Fixtures and browser prototypes must be visibly simulated. Real model calls remain 0 until a separately recorded real run; design checks do not establish server-side authorization or durable execution.
- Do not commit local databases, board keys, authentication material or private executor logs. Preserve archived input bytes and historical evidence; write new validation results to a new directory.
- Cloud tasks already have an isolated checkout; use it rather than creating worktrees unless the user explicitly asks.
