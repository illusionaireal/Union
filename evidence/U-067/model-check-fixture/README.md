# Model-check fixture wait contract

2026-11-08. PR33 Windows job128762174256 timed out in the five-second
ModelAccessCase.wait_for while the second original attempt remained dispatching.
The full local 754-test run and isolated race test pass; the original failure is
retained in coordinator-validation.json. This contract precedes the fixture fix.

Only the test helper polling budget changes: default 30 seconds, optional explicit
short budget retained. Product model, cancellation, recovery, authorization and
terminal-state semantics do not change. Waiting performs reads of the original
check; it never replays the start command or dispatches another model attempt.

A real local HTTP/SQLite check using the explicit model double will hold its first
request for 5.5 seconds. The original five-second default must fail to observe its
otherwise valid completion. The fixed helper must return the same original check
with exactly two original model requests. A separately supplied short budget must
still fail while pending; releasing that same request then completes without a
new start or replay. All original result and usage assertions remain.

Observed RED: the original default actually failed on the pending original HTTP check; the newly specified explicit timeout was unsupported (one behavior failure, one TypeError across two tests). After the two-line fixture change, all 10 fixture/model-observation checks pass. The 5.5-second request still produces exactly two distinct original model request IDs, and the 0.05-second wait still fails before querying the same completed check. See [verification](verification.json). Full-suite and current-head CI remain required before adoption.
