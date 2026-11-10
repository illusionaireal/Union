# U-092: superseded recovery replay changes ownership before rejecting

2026-11-10. Independent review by the single codex-home duty session, distinct
from developer session `01a1c217`. Original #46 ownership remains unchanged.

**P2: a superseded recovery command is allowed into the preparation transaction.**
After a replacement recovery completes, resubmitting the old envelope returns
HTTP 409 but changes the original attempt's execution epoch from 2 to 3 and
commits another preparation event. Rejection therefore does not leave the
replacement's completed ownership facts intact.

In `application/work_recovery.py`, the first transaction finds the old recovery
record without checking its phase. It updates its host/epoch, updates the
attempt and persists `recovery_prepared`. Only the final transaction requires
`record.phase == prepared`; the old record still says `superseded`, so that
check rejects after the earlier transaction has committed.

This is an additional finding on the unchanged candidate covered by the
[earlier lifecycle review](../duty-review-20261110/README.md). It does not
replace those two dispatch findings or claim that the product was repaired.

The [contract](contract.md) was frozen before the [HTTP/SQLite probes](probes.py):

| Original recovery replay | HTTP | Attempt epoch | Durable state |
| --- | ---: | --- | --- |
| Completed original, positive control | 200 | 1 → 1 | Unchanged |
| Superseded, replacement completed | 409 | 2 → 3 | **Changed: FAIL** |
| Superseded, replacement still prepared | 409 | 2 → 2 | Unchanged |

Three tests: two pass, one assertion fails, zero runtime errors. Each scenario
uses one initial fake model request; all recovery/replay operations issue zero
new model POSTs. Real inference is zero. Original Work/attempt/request IDs and
the replacement result are retained. No author product file was modified.

The isolated candidate is integration `63c4030` plus the same 20 author files
as the earlier source manifest
`37b49c71de59f9cdad4ab0358a703df6deaa5f980336373a6eea3d8947c30148`.
All hashes were rechecked in both author and isolated copies after probing.
[Validation](validation.json) records the exact input, observations and log
hash. This is a prepublication snapshot, not an approved product commit.

Prerequisite: `63c4030` plus **all 20 unpublished author files**, matching the
source map in [lifecycle validation](../duty-review-20261110/validation.json),
including `tests/test_work_recovery.py`. The evidence-only PR76/77 and clean
integration `faa5a4c` do not contain that implementation/fixture. A clean clone
alone cannot reproduce the product failure; obtain the original snapshot
from its owner, or an explicitly identified repaired candidate.

Run the complete review package with pinned Python:

```text
python -B evidence/U-092/superseded-recovery-review/probes.py <candidate-source-directory> <private-result.json>
```

Missing/mismatched inputs now exit **2**, write an input diagnosis and run
**zero** tests before any candidate import. The historical snapshot exits
**1** with the original one behavioral failure. See the
[revised-input procedure](../review-inputs/README.md) to bind a repaired
candidate; passing these probes alone is not product approval.

The original owner should reject or project an already superseded request
before any preparation mutation. Preserve original command identity and
history; do not delete the record or reset epochs. Include the counterexample
and positive controls in the implementation's regression suite, then publish
the exact product head for independent review and full current CI.

This delivery contains review evidence only. Local verification is the new
bounded negative probe plus structural/hash checks; full Python/npm/browser
product acceptance was not rerun or claimed for the rejected unpublished
candidate. CI on this evidence PR cannot approve that candidate. #46 remains
in progress; #47/#52 dependencies and real parent acceptance remain unchanged.
