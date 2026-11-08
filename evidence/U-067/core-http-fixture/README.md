# V1 HTTP fixture timeout follow-up

2026-11-08. Implementer: codex-home, online member
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`; Kanban #22 comment #68.
DSH retains the original card and PR #22 acceptance drivers.

PR #28 at `4494b758348312f71d37d00e4db7e99fd92fdaab` failed Windows
[job 128721896081](https://github.com/illusionaireal/Union/actions/runs/42477468161/job/128721896081):
725 tests, one error, nine skipped. The failure was a five-second socket wait
in `CoreCreationTests.request` during fixture creation in
`ResponsibilityTests.setUp`, before the responsibility assertions. The other
same-head Windows run succeeded. The earlier PR #27 repair covers the separate
legacy HTTP helper and remains intact.

The [contract](contract.md) was frozen before the change. The new
[executable probe](probe.py) delays an actual V1 creation by 5.5 seconds.
On unchanged source it raises the same TimeoutError ([RED](red.txt)). Changing
only the helper's default wait from five to 30 seconds returns the original
saved receipt and a single AU after exactly one POST. An explicit short timeout
still raises, and the subsequently committed original receipt is queried without
another POST. Both checks pass ([GREEN](green.txt)). Product code, identity and
authorization assertions, CI limits and explicit timeout arguments are unchanged.

Run from the repository root:

```sh
python evidence/U-067/core-http-fixture/probe.py
python evidence/U-067/independent-review-probes.py .
python -m unittest discover -v
npm run check
```

The completed checks are indexed in [verification.json](verification.json):
Python **725 tests, eight skipped, passed**; `npm run check` passed, including
220 frontend tests and 37 management checks; the original three S03 probes
passed. These completed local runs were recovered when this same fixture task
resumed; the helper and product source had not changed. The resumed run also
passes both real delayed-response probes and all 40 affected creation,
entrypoint, participant and responsibility tests before publication. Log hashes and the
helper's exact Git blob identify the retained evidence without publishing host
paths or private logs.

The new probe is standalone evidence, so it does not add a deliberate
5.5-second delay to every regression suite. The original failing Windows CI
run remains failed; the published commit needs a fresh protected CI run.

This is a controlled fixture repair, not new model or business acceptance.
Real model calls: zero. No NAS service switch or live-data migration. PR #28
retains the reviewed PR #26/#27 history; PR #24/#25 and the combination still
require another engineering role's adoption review and successful current-head
CI. No earlier failing check is relabeled as success.
