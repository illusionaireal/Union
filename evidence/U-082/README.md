# U-082: independent review of the V1 HTTP fixture wait

2026-11-08. Kanban execution card #36, parent #22 / U-067. Reviewer:
chatGPT-online, online member `54f3ed9e-817b-482a-90c1-d46bfc01728c`;
actor: Codex / GPT-6 / current Work Mode session. codex-home implemented the
fixture change and requested this separate review in team message #38.

## Review boundary

Candidate: PR [#28](https://github.com/illusionaireal/Union/pull/28) at
`894f5106a105a9ab269ef9035c9a40f36e5d791c`, against its actual parent
`4494b758348312f71d37d00e4db7e99fd92fdaab`. The increment changes only the
default socket wait in `CoreCreationTests.request` from five to 30 seconds,
adds two explanatory comments and fixture evidence. Product source, other test
assertions, explicit caller timeouts, CI configuration and the previously
reviewed legacy HTTP helper are unchanged. Thirty seconds bounds each blocking
socket operation; it is not an end-to-end business deadline.

This is one small independent verification result, estimated at 0.5–1 hour.
It does not approve PR #24/#25 or PR #28's combined product changes, authorize
their adoption, or complete the parent's real S03 acceptance. The parent retains
its original owner, dependencies, unfinished acceptance and WIP. DSH's real
drivers/099/100 remain outside this review. No production changes or model calls.

## Independent reproduction

The [frozen contract](https://github.com/illusionaireal/Union/blob/894f5106a105a9ab269ef9035c9a40f36e5d791c/evidence/U-067/core-http-fixture/contract.md)
and [executable probe](https://github.com/illusionaireal/Union/blob/894f5106a105a9ab269ef9035c9a40f36e5d791c/evidence/U-067/core-http-fixture/probe.py)
were reviewed on that exact candidate. The probe delays the real loopback
creation command; it still calls the original product implementation.

For RED, the reviewer loaded `tests/test_core_creation.py` from the actual
parent commit with `git show`, executed it in a separate in-memory namespace,
and bound only its original `CoreCreationTests.request` to the probe. No normal
source was disabled or edited. Both probe tests ran: the 5.5-second default-wait
case raised `TimeoutError`, and the explicit short-timeout case passed. The
runner asserted exactly that one error, rather than treating any failure as RED.

On the unchanged candidate checkout, both probes passed. The default call sends
one original POST, returns its successful receipt and matches the subsequently
queried receipt and single persisted AU. The explicit 0.1-second timeout against
a 0.5-second delayed command still raises; the original command then commits and
is recovered by GET without another POST. The helper closes its connection in
`finally`, and contains no retry loop.

Commands from the candidate root:

```sh
.venv/bin/python evidence/U-067/core-http-fixture/probe.py
.venv/bin/python -m unittest -v tests.test_core_creation tests.test_core_entrypoints tests.test_core_participants tests.test_governance_responsibility
.venv/bin/python evidence/U-067/independent-review-probes.py .
.venv/bin/python -m unittest discover -v
npm run check
```

Measured results, source identity, log digests and current-head CI are indexed
in [verification.json](verification.json). Local checks use Linux, Python
3.12.14 and Node 24.22.1; remote CI supplies the pinned cross-platform checks.
Private host paths and raw environment logs are not published.

## Conclusion

The fixture increment is accepted within this controlled scope. Independent local
validation passed: two delayed-response probes; 33 affected tests; three original
S03 probes; Python 725 tests (2 skipped); and npm check (220 frontend,
37 management and nine action checks). All three current-candidate CI workflows,
including seven Linux/Windows/browser jobs, passed. The prior Windows failure remains historical failure, not relabeled
as success. Engineering fixture verification cannot substitute for real model,
resource, interruption or sustained-operation acceptance.
