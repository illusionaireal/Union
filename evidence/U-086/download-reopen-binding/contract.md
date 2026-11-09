# Download restart binding repair

2026-11-09. Implementation actor: the single codex-home duty session; online
member `c18f0d21-1d63-4e37-af3e-2dbb78d75995`. This is scoped assistance to
DSH's #40, without changing its owner, status, or real acceptance.

Freeze before RED: author input `9d1435b` contains current integration
`a401d2b`. Repair only `scripts/exit22c_download.cjs`'s restart observation.
The other file, `exit22b_page.cjs`, has a `settledStep` assertion; the download
file's restart block does not. Do not mix those independent assertion blocks.

One outcome, estimated 1–2 hours including validation: a successful download
reopen proves the same delivered Work and the original adopted result survived.
This small repair needs no separate technical-layer cards. It does not change
Core, modeld, governance, transactions, invocation limits, or dispatch loops.

Acceptance:

- Read the original Work snapshot once, require HTTP 200, `core.work.v1`, and
  the original AU; a matching body returned with HTTP 403 is not success.
- Find the original Work and require `delivered`.
- Find the original result by ID (not the first adopted result), require
  `adopted`, its original SHA256, and `delivered_result_id` equal to that ID.
- Preserve a passing original-result control including an additional adopted
  result preceding it. Reject changed/missing identity, scope, digest, status,
  or delivery binding. Do not prescribe the number of diagnostic checks.
- Use the exact source block with synthetic fetch/page inputs. Await it;
  demonstrate synchronous and post-await assertion failures are observed,
  while unexpected runtime errors remain errors. Never run the real driver,
  browser, host, credential loading, or model requests during these probes.

Record baseline RED before editing the assertion, then GREEN and full project
checks on the candidate source. Preserve earlier failure/real evidence. The
repair cannot supply missing same-run snapshots, remote accounting or Work
events, cannot validate past real runs, and cannot close #22/#39/#40.

The checkout's pre-existing U086 edits and vendor state remain untouched. A
task-owned temporary Git index may build the assistance branch from the exact
author input without changing the existing checkout/index. Only this repair,
its probes, and its evidence enter the assistance diff. The author receives a
draft PR; candidate implementation is not an independent approval.
