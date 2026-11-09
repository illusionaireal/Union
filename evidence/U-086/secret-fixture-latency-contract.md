# U-086 integration: credential fixture timing contract

Frozen before changes, 2026-11-09. PR48 exact head
`23aeb36a78f51734488112d97f172a817c237128`, Windows job `128957645080`,
failed a safe-output assertion: one provider POST and preserved native events,
but `interrupted/provider_result_unconfirmed`, no final result or usage.
The other Windows job on this head passed. This does not prove the specific
cause of the failed CI run; the provider exception is intentionally private.

Investigate the fixture's one-second idle and three-second total deadlines with
a deterministic delayed safe response. The security suite tests disclosure and
retention, not a one-second latency service objective. Its ordinary response
must survive a 1.2-second gap between safe text and final usage/finish frames.
Use the unchanged kernel/server and a real loopback HTTP stream. Observe RED
before changing fixture deadlines. An interrupted response must still fail the
existing completed/output/usage assertions; do not change product deadlines,
credential checks, error classification, vendor files or CI gates.

The minimum repair may give these synthetic requests a larger bounded deadline
and a compatible bounded observation window. Cancellation and credential
rejection cases must retain their existing assertions, one provider dispatch,
zero external calls and original event/usage retention. The dedicated kernel
timeout regression remains required. Keep the failing CI evidence and the
deterministic RED separately; the latter is not a claim to reproduce Windows
scheduler history exactly.

Scope: one 1–2 hour integration test repair under #40, no separate product
outcome or artificial split. Original DSH owner/WIP and real #22/#39/#40 exits
remain open. Test fixture only; no model spending, live migration, service
switch, supervisory script or host configuration changes.
