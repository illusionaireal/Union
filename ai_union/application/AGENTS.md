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

- `model_events.py` projects only saved S02 text events for the current governor.
  It rechecks session/AU/connection after the original modeld grant GET, never
  dispatches, reconciles or writes. Native context and tool arguments stay private.
  Follow `s09-model-observation-contract.md` and `tests/test_core_model_events.py`.

- `work.py` starts S03 V1 work inside the same GovernanceStore transaction and
  returns the original receipt for a repeated request. It revalidates the
  logged-in principal, locates the actual AU, requires the active governor and
  a live adopted default connection, then registers Member/Definition/binding/
  Work/Mandate. Its read projection reports whether the referenced materials
  root is registered and how many documents are readable, without reading
  content. `invoke_tool` runs one authorized read-only tool through
  `adapters/documents.py` inside the same transaction and records its
  receipt there; it never calls a model. `result_content` serves a result body
  read-only and re-checks its digest on every read. Attempt lifecycle commands record
  ownership and call-budget facts in the same transaction and never start
  execution or spend a call by themselves. Automatic channel outcomes still use
  this sole AU writer; verify
  tests/test_core_work.py with S01/S02/S05 regressions.

- U106 result governance eligibility is independent of model-start eligibility.
  Explicit result adoption may close only its proven completed original loop
  attempt in the same transaction, using saved loop/step receipts; unknown or
  later execution stays open. Work delivery still requires an adopted result
  and no running attempt. Scoped downloads bind AU/Work/result and verify the
  digest. Follow `s03-result-delivery-contract.md` and `test_core_result_delivery`.

- Automatic work turns use `work_context_store.py` within that same transaction
  to retain private assistant/tool messages, native context and original tool
  sources. Before redisclosure, recheck the current work scope, root binding and
  snapshot digest. Never expose these private inputs in AU projections or
  rebuild them by rereading files. Follow `s03-tool-context-contract.md` and
  `tests/test_work_context.py`; dispatch intent now follows the contract below.

- Completed modeld calls that lose authorization keep their original request
  ID and usage as used steps; `record_channel_outcome` never adopts their
  content or runs returned tools. Follow
  `specs/053-union-rewrite/s03-model-observation-contract.md` and verify
  `tests/test_work_observation.py` together with dispatch recovery tests.

- `work_dispatch.py` records prepared/observed dispatch facts through the same
  GovernanceStore transaction. Persist the original command digest, scoped
  model request, responsibility versions and reservation before calling the
  transport. Replays return the original receipt or unresolved intent; never
  POST an unknown request again. Accounting survives revocation/session loss;
  content/tool adoption separately checks current authority and host material
  binding. Legacy `reconcile_step` queries usage without adopting a body;
  U-092 explicitly recovers sealed original observations through the shared adopter.
  Follow `s03-dispatch-contract.md` and `tests/test_work_dispatch.py`.

- U-092 `work_recovery.py` owns same-attempt recovery, owner/epoch admission,
  recovery-busy exclusion and original-request lookup. `work_dispatch.adopt_turn`
  is the sole normal/recovery result, tool and context adopter. New dispatch commits
  its complete private request and prepared boundary with the original reservation.
  Dispatching and final current authorization/owner admission precede POST; network
  calls hold no AU/catalog/global mutex. Close does not remotely cancel an admitted
  in-flight call; late workers cannot act/adopt/settle a new owner's reservation.
  Complete observations/usage survive privately before adoption. Current-owner
  continuation never increments epoch or replays POST; command replays return
  immutable receipts only. Verify `test_work_recovery*`, old dispatch/context/
  observation and schema compatibility checks.

- `work_events.py` owns only the current governor's read projection of the
  original Work step's modeld journal. Bind saved AU/Work/attempt/command/step/
  request and connection/grant versions, recheck local and remote authority
  around network reads, and keep those reads outside account/AU locks. No
  grant creation, reconciliation, reservation writes or dispatch. Follow
  `evidence/U-108/contract.md` and `tests/test_core_work_events.py`.

- U-120 `materials.py` composes import/revoke and read-only metadata discovery
  through the existing GovernanceStore and MaterialStore. Normalize import
  payloads to a content digest before durable receipts; preserve original IDs.
  `work.py` consumes the versioned source at dispatch, tool and acceptance
  boundaries. Imported invoke reads return metadata without copying private
  text into issuer receipts. No second writer, dispatch loop or read migration.

- U-093 `work_inputs.py` accepts bounded private requirements through the same
  GovernanceStore transaction, with immutable actor/source/seq and digest-only
  commands. Receipt acceptance is independent of model/budget/attempt readiness.
  Original dispatch preparation freezes ordered input refs/messages/attachments;
  observation is separate from same-transaction `adopt_turn` context/consumption.
  Current authorization/source and owner are rechecked; unknown never rePOSTs.
  Trusted original loop children may absorb only audited low impact append
  version changes in the same AU, and select inputs only from their own Work.
  Public base versions and saved requests stay strict and immutable.
  Pending input blocks automatic result-attempt closure and delivery. Verify
  `test_work_inputs` plus work dispatch/recovery/context/loop/compatibility tests.
