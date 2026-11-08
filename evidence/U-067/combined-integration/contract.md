# Pending S03 candidates: combined integration check

2026-11-08. Implementer/integrator: codex-home. This is an integration check,
not the separate engineering review required to adopt these candidates.

Inputs are PR #24 `39db061`, PR #25 `4bce491`, and PR #26/#27 `9d60a94`,
on integration baseline `bbe8068`. The original contracts continue to apply.
No new product behavior or authorization is introduced by this check.

The combined tree must preserve a completed two-turn document/result exchange
alongside a different Work's unknown reservation, after a normal Console
restart. The authorized core tasks route must show both Works under schema 4,
download the exact persisted result, and retain the unknown original request
without dispatching it again. Refresh, reload and result reads must not write
Work commands. An expired session must not download the result.

The fixture uses real local HTTP/SQLite and an explicit loopback model double.
It asserts document content in the second outgoing model request, the document
digest in the stored tool receipt, actual result bytes, separate request IDs,
the preserved reservation and zero additional dispatches after restart.
These are controlled engineering observations, never real model acceptance.

The original three review probes and the combined Python/frontend regressions
remain required. Source conflicts must retain both histories. PR #22 drivers
and evidence 099/100 stay with DSH. No live AU, NAS service, supervisor, host
configuration or model credentials are modified. Individual PR review and
current-head CI remain adoption gates; this integration does not bypass them.
