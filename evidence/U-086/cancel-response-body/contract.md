# U086: recover a committed cancel after its response body is interrupted

Frozen 2026-11-09 before implementation, on PR63
`b446caf2a6507f283836e9009984d49f8c93541d`, descendant of current integration
`4aa020bf6e528d1d9bc6ab28c5aa8b63cc53fe5c`.

The single codex-home duty implementer continues #40 assistance; DSH retains
owner/progress/WIP and #60 remains done. This 1–2 hour correction has one
independently verifiable outcome; no split is needed.

- A cancel may commit and return HTTP 200 headers before its body is cut off.
  After that transmission ends, the acceptance driver must recover through
  the existing original cancel control and GET. It must submit exactly one
  cancel command and retain its AU/Work/step/model/principal/service binding.
- A transport failure is not a complete receipt. Do not compare missing body
  bytes with the durable receipt, or report remote cancellation from them.
  The existing full original GET and identity checks must still succeed.
- An observed non-200 status, including 401/403, must fail acceptance even
  when its body is interrupted and an older valid receipt can be queried.
  A fully transferred malformed or mismatched receipt also fails; it is not
  reclassified as a transport failure.
- Use the unchanged PR63 full output/cancel fragment against a disposable
  actual Chrome → Core HTTP → SQLite fixture. Truncate only the response
  after the existing command has committed; never remove working product
  behavior to manufacture RED. Keep original receipt/reservation persistence.
- Preserve PR63's eight browser cases and all existing assertion histories.
  No product, schema, runtime authorization, real inference, grants, business
  activation, deployment, migration, supervisor/config/lock changes.

The implementation needs exact-head CI and another engineering role's review
before adoption. This session does not independently approve itself or claim
completion of the real #22/#39/#40 exits.
