# Creation and governance application owners

- `creation.py` owns one creation sequence for legacy and core V1: durable
  intent/allocation, selected store, final registration/receipt, and unknown.
- Use the actual catalog/store adapters; never import Console or perform model,
  workspace, resource-grant or autonomous-business actions from creation.
- Revalidate the trusted account at intent acceptance. Existing IDs are
  authorized before payload comparison and never revalidated or replayed.
- Keep partial directories and original receipts; no read repair, automatic
  migration, duplicate AU, dual writer or cross-database atomicity claim.
- Verify identity, core creation/failures, legacy receipts and profile isolation.
- `governance.py` revalidates actual core identities, locates an integrity-checked
  AU and applies the pure governing rules within the sole governance store
  transaction. Account registration never grants AU authority.
- Current AU access and original-issuer receipt access are separate. Original
  request lookup precedes current rule validation; do not replay unknown writes.
- No model/host dispatch, read migration, autonomous business or legacy Engine
  writes in this owner. Verify tests/test_governance*.py with S01 regressions.
