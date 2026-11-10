# U-086 independent review of revised session and replay candidates

Frozen 2026-11-10 before execution. Actor: Codex session
`01a1c5eb-0bf1-7082-b001-ed1e0460a9bc`. Authenticated Kanban member:
`codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`.
Neither is a product AU member. Original #40 ownership remains with HOME-GOOSE.
Online scope: comment 379, 1–2 focused hours, one review decision, no split.

The exact candidate is `da316ed309c105694b1826be581d55857b2016d9`, including
session change `1730a1161c3c59b7d4089fd9642bdbe96110754b`. Later
`49ba76276da5d53e9445a8c64a8f2aa1a54abed7` adds one author probe and changes
no candidate implementation. Export from Git into a new private snapshot and
bind every reviewed input before imports. Missing or changed input is exit 2
with zero behavior tests, not a product failure.

1. Rebind the original four session/catalog HTTP probes without changing their
   behavior assertions. Preserve healthy and scoped controls and catalog/state
   byte checks. Record the exact path and error code of any remaining rejection.
2. Separately retain the existing damaged-creation-audit test: it requires 409.
   A remaining original isolation assertion does not authorize widening a catch
   to hide damaged identities. Distinguish an unresolved scope/contract conflict
   from an instruction to suppress integrity failures. A prepared V1 AU's actual
   readability must be established by real creation fixtures, not a stub error.
3. Rebind the prior replay probes to the revised call order and explicit
   `status: unchanged`, `dispatch_count: null` schema. Record these adaptations;
   preserve the original files and their historical failures.
4. Execute the exact candidate driver segment including both recorder and
   comparison. Healthy unchanged snapshots must record the explicit unknown
   dispatch count and must not add a successful dispatch check. Added requests
   must still be rejected and leave a failed observation.
5. Exercise valid same-count changes to original request identity and result
   content. The existing strict comparison must reject them. Its durable
   observation must not claim unchanged persisted facts or zero differences on
   that failure. A recorder that only counts requests cannot decide these cases.

All HTTP fixtures are temporary local synthetic databases; replay uses an
in-memory filesystem and no network. Run author controls and relevant integrity
tests once. On an unresolved counterexample, report a bounded negative review;
do not claim full npm/Python/browser/CI adoption, real cancellation or replay.
No product changes, model calls, migration, deployment or author checkout writes.
