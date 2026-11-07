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

- S02 `model_access.py` and `model_checks.py` own configuration/resource and
  bounded verification rules. The explicit grant is separate from the original
  resource plan; every check links a real human Member/Work/Mandate to a
  separately versioned Agent Definition. No legacy Engine or host calls.
- Charter `read_document` is V1-only. Ordinary legacy validation stays strict.
  Current versions and authority are checked for every model/tool/acceptance
  boundary, while historical usage remains factual after revocation.

- S03 `work.py` owns V1 work responsibility rules: one goal, one AI Member,
  one Agent Definition version, one binding and one root Mandate created
  together under the active current governor. It rejects host paths, tools
  outside the effective charter, unknown connections and call caps beyond the
  AU plan. `read_document` additionally requires a registered materials
  reference, and stored work records keep that consistency. `invoke_tool`
  validates each call against the responsible member's live Mandate, caps
  durable receipts, and keeps document content out of AU state (only
  digest, size, arguments and step_ref are recorded). `start_attempt` /
  `finish_attempt` own the execution-ownership boundary: only one running
  attempt may act, a closed attempt cannot act again, and an `unknown`
  outcome blocks new attempts and tool calls until it is explicitly
  resolved with a recorded reason. `reserve_step` / `settle_step` own the
  per-call budget: one reserved call per step, capped by the work plan,
  purpose and attempt recorded, `unknown` keeps its reservation and a
  settled step can never be re-judged. An attempt also records the host
  service instance that owns it; after a restart the attempt reads as stale
  and cannot act until it is settled through finish_attempt. No model call,
  storage or dispatch; step S03.2+ extends the same owner.
