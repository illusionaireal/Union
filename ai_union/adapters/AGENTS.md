# AU persistence adapters

- Follow the root AGENTS, ADR-0005/0006 and the active S01 contract.
- S05 extends the explicit contract in specs/053-union-rewrite/s05-contract.md.
  `governance_store.py` alone writes adopted V1 governance state, audit and
  receipts. The explicit first adoption snapshots schema 1 bytes, then moves
  that AU to schema 2 in one SQLite transaction; reads never migrate.
- Authorized initial rule/version refusals keep their original command receipt
  in schema 1 without adopting governance or rewriting creation facts.
- CoreAUStore validates original creation against its catalog intent separately
  from the current version/audit chain. Current authority lives in the AU;
  catalog creator remains the original creation-receipt owner only.
- `au_catalog.py` owns read-only validation of a catalog locator against the
  stored AU identity before Console/discovery callers construct a runtime.
  The catalog is a locator; the AU database owns its ID/profile.
- Reject incompatible or incomplete mappings; do not repair, create, migrate,
  register, dispatch or pause an AU from this resolver. Credentials and host
  paths must not appear in public diagnostics.
- The shared creation application uses `creation_catalog.py` as the only
  creation-intent/registration writer and chooses `legacy_au_store.py` or
  `core_au_store.py` by explicit profile. V1 has no Engine or board.key.
- New allocation validates the resolved directory before any filesystem write.
  Reopen/lifecycle validation matches the V1 adoption to the unique original
  intent, principal, AU ID, profile, charter, content and creation time.
- The AU database transaction holds state/root, initial charter and adoption.
  Catalog registration remains a separate transaction; unknown never rebuilds.
- Keep transactions explicit and handles closed. Do not claim an atomic
  transaction spanning catalog, AU databases and filesystem paths.
- Preserve original creation payloads/receipts and unknown recovery. Required
  tests include catalog integrity, Console, HTTP, AU contract and mechanisms;
  run the full fixed-toolchain checks before delivery.
