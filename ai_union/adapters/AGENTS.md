# AU persistence adapters

- Follow the root AGENTS, ADR-0005/0006 and the active S01 contract.
- `au_catalog.py` owns read-only validation of a catalog locator against the
  stored AU identity before Console/discovery callers construct a runtime.
  The catalog is a locator; the AU database owns its ID/profile.
- Reject incompatible or incomplete mappings; do not repair, create, migrate,
  register, dispatch or pause an AU from this resolver. Credentials and host
  paths must not appear in public diagnostics.
- S01a supports existing legacy storage only. Stable principals, V1 storage,
  schema upgrades and prepared-AU entry isolation remain S01b/S01c work.
- Keep transactions explicit and handles closed. Do not claim an atomic
  transaction spanning catalog, AU databases and filesystem paths.
- Preserve original creation payloads/receipts and unknown recovery. Required
  tests include catalog integrity, Console, HTTP, AU contract and mechanisms;
  run the full fixed-toolchain checks before delivery.
