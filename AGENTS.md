# UNION repository instructions

- Read README.md and docs/kickoff/STATUS.md first; baseline documents are in docs/baseline.
- Preserve PLAN/OPS/ENG identifiers. Baseline files are historical inputs; record execution status separately.
- Stay within M0 scoped experiments until PLAN-001–006 are accepted with evidence. Preparing code does not complete ENG tasks.
- AI runs the Union business; investors do not approve daily operations. Separate platform work from business intervention.
- Keep mock, testnet, and real funds distinct. No real payment, marketing, model spending, signing, or external deployment is enabled by this spike.
- Amounts use integer minor units with explicit currency. Unknown external results retain reservations and require lookup.
- Money and authorization changes require another engineering role's review before adoption. Tests alone do not satisfy that review.
- Run npm run check before proposing changes. Record limitations and do not present SQLite tests as PostgreSQL/Temporal validation.
- Do not change repository visibility or choose an open-source license without an explicit project decision.
