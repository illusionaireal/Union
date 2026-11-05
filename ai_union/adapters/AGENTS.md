# AU persistence adapters

- Follow the root AGENTS, ADR-0005/0006 and the active S01 contract.
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
