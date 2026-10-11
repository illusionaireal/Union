# ai-union development

Read `HANDOFF.md` and `specs/001-org-bootstrap/` before continuing this iteration.
Read `docs/PRD.md` and `docs/product-design.md` before user-facing product work; keep product scope, flows, design and acceptance aligned with the latest user decisions before implementing new views.
The runtime's adopted organization charter is application data; it never replaces these development rules or host authorization.

- Keep industry positions, strategy and content workflows out of production code and prompts. Fixtures must be visibly simulated.
- Bind acting identities in the host, validate current authority and versions, and submit state/decisions/dispatch records transactionally.
- Unknown external execution is a reconciliation condition. Do not silently retry it.
- Test changes to authority, persistence, handoff, wakeups, resource accounting and executor protocols with meaningful behavioral tests.
- Run `python3 -m unittest discover -v`. CLI operation is `python3 -m ai_union` from the checkout.
- Do not commit local databases, board keys, authentication material or private executor logs. Never label fixture results as real Agent or market evidence.
- Cloud tasks already have an isolated checkout; use it rather than creating worktrees unless the user explicitly asks.
