# U-086: actual Core result adoption and delivery gate

Frozen before test/driver edits, 2026-11-09. Input 76807aec2221fb5bbdacb3009b3c2020f6f9275b.
Actor: current single codex-home duty session; online member c18f0d21-1d63-4e37-af3e-2dbb78d75995. DSH retains #40 ownership, progress/WIP and history.

One bounded acceptance-driver repair, estimated 2–4 engineering hours including validation; no split because page actions and exact persisted delivery constitute one independently verifiable outcome. This does not implement a new product slice or authorize real inference.

The existing download driver must adopt and deliver through the actual Core /tasks controls scoped to the original Work and result ID. Hidden/disabled/missing controls, rejection, or a still-running attempt must fail the gate. No direct adopt_result/deliver_work POST, manual finish_attempt, alternate result, or repeated action may repair the acceptance scenario. The UI owns fresh identity/version checks and command persistence.

Before and after action reads use the existing authenticated session/Work/session snapshot. The same principal, AU, Work, original result ID, digest and sources must survive. Success requires BOTH Work delivered with delivered_result_id equal to the original result AND that original result adopted; adopted alone is insufficient. Browser actions must be observed, and the final artifact records their original command IDs. On uncertain POST outcomes the driver fails without replay; existing page recovery remains available with the original ID.

Keep original download byte/digest/title/AU/Work assertions and downstream authenticated restart/request/usage/budget comparisons. No manual body or finish controls are exposed. Existing API registration, model/profile authorization, full original-output evidence and historical real-run claims remain separate unresolved acceptance boundaries.

Validation: meaningful old-driver RED, minimum driver-only GREEN, actual Chrome/Core HTTP/SQLite with the existing two-turn fake candidate, Node/management/npm/Python and exact-head CI. Missing controls and incomplete/wrong delivery must reject without hidden API writes. No product source, models, real data, supervisor, configuration, locks or schedules change; another engineering role reviews the candidate before adoption.
