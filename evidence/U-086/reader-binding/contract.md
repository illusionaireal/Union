# Original output reader through cancellation recovery

2026-11-09. Scoped assistance under #40 / U-086, comment260. DSH retains
ownership and progress/WIP. The single codex-home duty session implements this
repair; another engineering role must review it before adoption. Estimate:
1–2 focused hours, one independently verifiable driver defect, no split needed.

Base: `abef54404dfd2b440bd602082013e7adda21bb58`. Its output gate verifies
the session and events reader, but omits the reader from `outputObservation`.
The following original cancel reference consumes `outputObservation.principal_id`.
Its required-reference assertion therefore rejects the legitimate sequence.
Separate tests supply a synthetic reader and miss this composition failure.

- Persist the principal and service from the already validated observation
  boundary alongside the original request IDs, UTF-8 count and text digest.
  Do not store raw output, credentials or authentication material.
- Build the original cancellation reference from that actual observation.
  Never substitute the reader of a later session or the receipt's asserted actor.
- Preserve current session/Work/receipt/session checks, original request and
  complete receipt equality. Changed principals or in-flight service changes
  reject. A service restart with the same principal can recover the original ID.
- Test the real output gate and downstream cancel/restart fragments together,
  without injecting `outputObservation`. Synthetic responses and existing fake
  transports suffice; do not run either real driver main or spend model quota.
- Observe a normal-sequence RED on unchanged base, then the minimum repair and
  paired authorization regressions. Keep all historical failures and evidence.

No product API, permission, transaction, loop, accounting or schema changes.
This fixes an acceptance driver; it does not validate historical139, turn API
registration/adoption into a page journey, or establish real remote dispatch
counts. #22/#39/#40 remain incomplete. The existing dirty checkout and ordinary
index are preserved; exact source validation and a task-owned index produce
the assistance branch without switching or replacing anyone's files.
