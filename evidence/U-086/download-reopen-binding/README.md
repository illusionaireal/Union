# Original download result after restart

2026-11-09. Scoped assistance to DSH's #40 (comment 216). The single
codex-home duty session implements this candidate; this is not independent
approval and does not complete real acceptance.

The current driver can accept HTTP 403 with a matching body, another AU, a
changed/missing digest and missing delivery binding after restart. It also
rejects a valid original result when another adopted result appears first.
The repair reads once and requires HTTP 200, core.work.v1, the original AU,
delivered Work, original adopted result ID and SHA256, and that Work's
delivered_result_id. Missing records are rejected explicitly.

The [original contract](contract.md) and [current continuation](continuation-contract.md)
were frozen before their respective RED runs. Historical baseline 9d1435b
had 11 failing assertions/0 runtime errors out of 17; the original
[RED](red.json) and [GREEN](green.json) are retained. The unpublished b189a88
candidate is retained as a parent.

On author 7f50feff31ab6c2275e160dcea518498155f540c, the same [17 probes](current-red.json)
have 11 failing tests: eight falsely accepted counterexamples, one rejected
valid control, and two TypeErrors (missing Work/unadopted result). unittest
counts the TypeErrors as assertion failures because the probe asserts that
there is no runtime error; they are not successful behavioral rejections.
The separately exercised async-runtime control remains classified as runtime
failure. After the minimum repair, [all 17 pass](current-green.json).
The [Node regression](../../../tests/exit22c-reopen.test.ts) adds 11 assertions
to normal npm test and runs only the actual restart block with synthetic input.

The candidate preserves all author bytes outside the download restart block;
in particular, the interrupt driver and historical real records are unchanged.
Author flow-specific interrupt assertions are not used to relax this delivered
download flow. Review check counts are not an acceptance condition.

The first full run lacked the locked modeld vendor/dependency links in the
validation snapshot: 798 tests, 1 setup JSONDecodeError, 10 skips. It did not
reach the SDK test behavior. After verifying the pinned upstream commit,
recorded patch (same Git abbreviation) and lock hashes, read-only dependency
links restored the same SDK/loopback test without product changes. The first
run and failed startup recheck are retained; the prepared full rerun is
recorded separately.

Full checks, canonical Git source hashes, exact tested commit and private-log
hashes are in [validation.json](validation.json). No private logs are published.
The draft PR targets the author branch, not rewrite. Current-head CI and another
engineering role's review remain required before adopting this implementation.

Reproduce the isolated probes with pinned Python/Node:

```text
python evidence/U-086/download-reopen-binding/probes.py 7f50fef red.json
python evidence/U-086/download-reopen-binding/probes.py <candidate-commit> green.json
node --test tests/exit22c-reopen.test.ts
```

No real driver main, model, browser or host ran for these probes; the full unit
suite uses synthetic transports. This does not supply missing same-run
snapshots, remote dispatch/billing evidence, Work output events, or real page
acceptance. #22/#39/#40 remain open. Workspace dirty files and the existing index
were preserved byte-for-byte through a separate task-owned Git index.
