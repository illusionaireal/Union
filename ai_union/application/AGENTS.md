# Creation application owner

- `creation.py` owns one creation sequence for legacy and core V1: durable
  intent/allocation, selected store, final registration/receipt, and unknown.
- Use the actual catalog/store adapters; never import Console or perform model,
  workspace, resource-grant or autonomous-business actions from creation.
- Revalidate the trusted account at intent acceptance. Existing IDs are
  authorized before payload comparison and never revalidated or replayed.
- Keep partial directories and original receipts; no read repair, automatic
  migration, duplicate AU, dual writer or cross-database atomicity claim.
- Verify identity, core creation/failures, legacy receipts and profile isolation.
