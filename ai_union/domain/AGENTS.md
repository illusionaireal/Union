# AU creation, governance and responsibility rules

- Follow the root AGENTS, Main V1, ADR-0005/0006 and S01 contract.
- `creation.py` owns pure charter/resource/input validation and prepared-state
  construction. No Console, Engine, SQLite, HTTP, Harness or filesystem imports.
- A caller supplies an already trusted principal and allocated AU ID; a display
  name, host session or platform-admin flag cannot supply governance authority.
- Keep the existing Engine validation imports as compatibility aliases to these
  rules; do not duplicate the rules or narrow the legacy CLI resource contract.
- Verify core creation, catalog/HTTP, mechanisms and legacy resource behavior.
- S05 `governance.py` owns the supported local governing program and current
  authority. Its rules receive trusted principals/time; no SQLite, Console,
  host-account or model calls. The initial root never becomes current authority
  by inference after a handoff. See specs/053-union-rewrite/s05-contract.md.
- Local responsibility is distinct from AI Execution. All action and result
  acceptance must consult the same current authorization/ancestor versions.
- `responsibility.py` implements the actual human internal-record use case:
  scoped Member/appointment/Work/Mandate chains, local attempts, unadopted
  late facts and checked result acceptance. No filesystem artifacts, models,
  automatic scheduling or alternate AU writers. Recheck every ancestor at
  action and adoption; preserve original obligations when stopping/handover.
