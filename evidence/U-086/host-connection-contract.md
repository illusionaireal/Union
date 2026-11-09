# U-086 acceptance host connection contract

Frozen before code changes, 2026-11-09. Scope: #40 comment 182, one 1–2 hour
assistance fix. Integration `902b429529f82aad6acc63c6fe4e69c4739ced17` is an
ancestor of author input `096815e44936e1f62a7b680b0d7a5f2db247eb1b`.
The author retains the card, page driver and unfinished real acceptance.

The acceptance host must exercise the same connection identity as production:

- `WorkService` supplies the authorized or original persisted connection to its
  transport factory. Preserve its `id`, `revision`, `grant_ref`, `grant_revision`,
  `model`, output limit and task limit without host defaults or replacement.
- Host configuration selects only the modeld service. A later `prepare` grant,
  a different AU/account/model environment, or a Console restart cannot rebind
  that original connection. Grant preparation remains explicit; it does not
  adopt a connection in the AU or give the host authority to change one.
- Reuse the existing product `modeld_factory`; it owns request construction,
  polling and scoped original-request lookup. Do not add a loop, transaction,
  reservation writer, replay or migration. Missing connection fields must not
  acquire synthetic identity/model/limits before dispatch.
- An original-request lookup performs GET only with the original AU/request ID.
  Transport creation and host restart do not dispatch or create grants.

Validation uses actual loopback HTTP and temporary Console state, synthetic
accounts/tokens and the normal product transport. First observe meaningful RED
on the unmodified author host, then GREEN and existing transport/full checks.
Never execute the real driver main or access a real model service in these tests.

This session implements the repair, so another engineering role must review the
candidate before adoption. No real inference, service switch or live migration
is authorized. The page driver's snapshot, output-before-cancel, settlement and
replay assertions remain separate author work. Historical evidence/127 is kept
unchanged; this fix cannot turn its earlier run into complete real acceptance.
