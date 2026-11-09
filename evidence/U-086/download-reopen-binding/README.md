# Original download result after restart

2026-11-09. Scoped assistance to DSH's #40, recorded in comment 216. The
single codex-home duty session implements this candidate; it is not an
independent approval and does not complete real acceptance.

Author `9d1435bc93c09278eac4664f974dac650cce651f` includes current integration
`a401d2b`. Its **download** driver still accepts any adopted result after
restart. The `settledStep` and delivered-ID assertions discussed in comments
210/212 belong to the separate **interrupt** driver. The executable reports
below include the exact download block and SHA256, so this is directly
checkable without inferring behavior from the other file or check counts.

After the [contract](contract.md) was frozen, [17 baseline probes](red.json)
produced 11 assertion failures and zero runtime errors. The original result,
an additional adopted result, existing status rejections and awaited VM
controls passed. Besides missing identity/digest/delivery binding and response
scope/status, a missing Work passed because `check(name, value = true)` turns
an undefined `entry && ...` argument into the default true. The repair uses an
explicit boolean at that boundary.

The minimal driver change requires HTTP 200, the original AU's `core.work.v1`
snapshot, delivered original Work, adopted original result and SHA256, and
its `delivered_result_id`. It finds the original ID among all results, so an
unrelated adopted result listed first does not reject a valid observation.
[The same 17 probes pass](green.json); runtime-error controls remain separate.
The [Node regression](../../../tests/exit22c-reopen.test.ts) runs the actual
restart block in normal `npm test` with synthetic responses.

Reproduce with the pinned Python and Node on PATH:

```text
python evidence/U-086/download-reopen-binding/probes.py 9d1435b red.json
python evidence/U-086/download-reopen-binding/probes.py <candidate-commit> green.json
node --test tests/exit22c-reopen.test.ts
```

Full project validation and exact candidate source hashes are recorded in
`validation.json` when completed. The assistance branch targets the author's
branch; it does not import the author's other drivers or historical real
claims into rewrite. Original failed evidence and pre-existing checkout edits
remain untouched. A task-owned temporary Git index constructs only this diff.

No real driver main, browser, host or model request ran for these probes.
This does not supply missing same-run snapshots, remotely verified dispatch
counts, billing, original Work events, or a full real page acceptance. #62 is
owned independently, and #22/#39/#40 real exits retain their own conditions.
