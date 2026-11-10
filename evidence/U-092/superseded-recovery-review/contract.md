# U-092 superseded recovery request review

2026-11-10. Independent reviewer: the single codex-home duty session;
implementation remains with the original #46 developer session `01a1c217`.
This bounded review does not claim the card or change its shared transaction.

Before running new probes, freeze this boundary from U-092 contract clauses
2–3 and ADR-0009: once a prepared recovery request is explicitly superseded
by a later recovery, replaying the old request cannot reacquire execution
ownership, increment the attempt epoch, or append a new preparation event.
It must expose its original superseded outcome or reject without mutation.
The replacement recovery and original Work/attempt/model request remain intact.

Use the author's temporary Console/HTTP/SQLite fixture with a fake model.
Interrupt the first recovery during the original-request GET, restart the
temporary service, and complete a replacement recovery. Then submit the
original recovery envelope again and compare durable state before and after.
Also cover replay while the replacement is still prepared, and a normal
completed-recovery replay as the positive control. Recovery must not POST a
model request in any scenario.

Run against an isolated snapshot, checking all 20 author-file hashes against
the previous review manifest before and after. Do not change product code,
author files, production data, credentials, supervision, or task ownership.
This is a 1–2 hour independent review increment; product repair and its full
acceptance remain the original owner's responsibility.

## Reproduction input clarification (2026-11-10)

This historical review requires the unpublished 20-file author snapshot,
including `tests/test_work_recovery.py`; clean integration `faa5a4c` contains
only evidence. The [input contract](../review-inputs/contract.md) now checks
the source map before imports and separates exit 2 input failure (zero tests)
from exit 1 behavioral findings. Original product expectations above remain.
