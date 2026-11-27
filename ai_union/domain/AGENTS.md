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
  initial service instance. U-092 keeps that history and separately tracks trusted
  current execution owner/epoch; a stale attempt acts only after explicit recovery.
  Legacy unknown/closed attempt settlement remains explicit. No model call,
  storage or dispatch; step S03.2+ extends the same owner.

- `work_recovery.py` owns pure owner validation, last-owner fencing and recovery
  eligibility. Current host/worker facts come from trusted application wiring;
  client host/owner/epoch never supply authority. Existing-owner continuation
  retains its epoch and requires an original unfinished sealed request or loop.

- Automatic step plans carry the current scope for private context integrity;
  active bindings/Mandates constrain all advertised and executed tools. Result
  sources include original tool receipts actually supplied to later turns.
  Private messages/storage stay outside this pure owner. See the S03 tool
  context contract and `tests/test_work_context.py`.

- `record_unadoptable_step` records completed model inference as used, including
  the original model request ID and observed token usage. Revocation denies
  content/tool adoption; it does not erase executed calls. Unknown remains
  reserved and used cannot be reconciled as released. Verify the scoped
  contract and `tests/test_work_observation.py` with existing work regressions.

- U-120 `materials.py` owns pure bounded text metadata and permission rules;
  private content has a separate adapter in the same AU transaction. Work
  bindings retain material ID/version/digest and never adopt a newer version
  silently. Revocation preserves obligations, original receipts and used calls.
  Follow `u120-business-materials-contract.md` and `test_business_materials`.

- U-093 `work_inputs.py` owns immutable requirement identity/source, bounded
  ordered metadata and continuous consumed-prefix validation. Acceptance never
  creates action/model/budget authority; source changes remain explicit pending
  facts. Consumed metadata must reference the original adopted step/context and
  observed attachment, with current adopted scope/owner retained separately.
  It has no database, dispatch queue, runtime loop or host dependencies.
