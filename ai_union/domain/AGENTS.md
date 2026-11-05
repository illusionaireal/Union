# AU creation rules

- Follow the root AGENTS, Main V1, ADR-0005/0006 and S01 contract.
- `creation.py` owns pure charter/resource/input validation and prepared-state
  construction. No Console, Engine, SQLite, HTTP, Harness or filesystem imports.
- A caller supplies an already trusted principal and allocated AU ID; a display
  name, host session or platform-admin flag cannot supply governance authority.
- Keep the existing Engine validation imports as compatibility aliases to these
  rules; do not duplicate the rules or narrow the legacy CLI resource contract.
- Verify core creation, catalog/HTTP, mechanisms and legacy resource behavior.
