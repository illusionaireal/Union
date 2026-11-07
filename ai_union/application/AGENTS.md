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

- `model_access.py` owns S02 authenticated configuration, durable intent and
  explicit original-request reconciliation through the same GovernanceStore.
  Network calls follow committed intent and occur outside account/AU locks.
  It cannot enumerate host accounts or invoke Engine for V1. API secrets go
  only to modeld; persisted commands contain a private digest, never the key.
  Verify tests/test_core_models.py and the S02 contract, preserving S01/S05.

- `work.py` starts S03 V1 work inside the same GovernanceStore transaction and
  returns the original receipt for a repeated request. It revalidates the
  logged-in principal, locates the actual AU, requires the active governor and
  a live adopted default connection, then registers Member/Definition/binding/
  Work/Mandate. Its read projection reports whether the referenced materials
  root is registered and how many documents are readable, without reading
  content. `invoke_tool` runs one authorized read-only tool through
  `adapters/documents.py` inside the same transaction and records its
  receipt there; it never calls a model. No harness step and no second
  writer; verify tests/test_core_work.py with S01/S02/S05 regressions.
