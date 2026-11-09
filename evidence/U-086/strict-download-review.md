# Strict download: independent review of bdbbb9b / 1d9ed8e

2026-11-09. The single codex-home duty session independently reviewed DSH's
download assertion change, requested in #40 comment 192. Fresh Kanban revision
593 confirmed U106/#60 already done via PR39, #40 still owned by DSH, and no
unowned ready task. Review scope and 1–2 hour estimate are in comment 195.
The implementation branch starts from actual integration `902b429`; it changes
only review evidence. It does not adopt the author's host or drivers.

**The reported download false positives are fixed; full original-result and
restart acceptance is still incomplete.** The exact source is
`1d9ed8e9ddcaed949d38218186ede28d216dfb8f`. Its driver and four inspected
evidence/129 inputs have identical SHA256s at `bdbbb9b`, the requested candidate.
This review does not rerun the paid acceptance script.

During this review the author published `b917eab749ae599c806453a497ad1b87b7641355`
and comment 196 for a separate interrupt-driver update/evidence/130. Fresh fetch
and API readback confirm it; all five download-review inputs remain byte-for-byte
identical. Executing all 11 probes again on exact `b917eab` also gives 7 passes,
4 assertion failures and zero errors. The downloaded-result findings therefore
still apply. The new
interrupt assertions are a separate pending review, not covered by these tests.
PR46 was meanwhile merged as `d209a0e073f2770f59787a02ca7a5ceb2f523ece` after
14/14 successful checks on `e91ae4e`; reviewed and merged trees both equal
`c5f71263c5cec5dd5ead05040140253a0ed0fe50`. That adoption contains only six
review-evidence files and does not adopt PR45's host or the author's drivers.

## Assertion results

The [contract](strict-download-review-contract.md) precedes the new
[reproducible probe](strict-download-review-probes.py). It extracts the exact
download/reopen blocks from Git and runs them with an in-memory HTTP response.
There is no driver import, browser, host, model transport or network request.
The [report](strict-download-review.json) contains input hashes and all outcomes:
**11 tests, 7 passing, 4 failing expectations, zero runtime errors**.

| Input / required boundary | Actual behavior |
| --- | --- |
| Original ID, title and UTF-8 body digest | Accepted; control passes |
| Error body, null result, other result ID | All rejected; the three earlier false positives are fixed |
| Changed body or title | Both rejected |
| Same result fields but another AU | Accepted; original AU check missing |
| Same result fields but another Work | Accepted; original Work check missing |
| HTTP403 with otherwise matching JSON | Accepted; fetch status discarded |
| Same original adopted result after restart | Accepted; control passes |
| Original result absent, another result adopted in the delivered Work | Accepted; original result check missing |

The last four are counterexamples to the assertions. They do **not** establish
that a real API returned a cross-AU result, disclosed data on HTTP403, or lost
the real result. The JSON/status mismatch is a synthetic response fault. The
author's narrower ID/title/content change is useful and should be preserved.

The first probe run used an unused synthetic protocol label
`core.work.result.v1`; it already produced the same four failures with zero
errors. The final run corrects the label to the actual `core.work.v1` response
from `WorkService.result_content`. The driver checks neither label; this fixture
correction changes no outcome. Both private logs are retained by hash.

## What evidence/129 supports

The saved Core Work after restart records **two distinct model request IDs**:

| Step | Status | Input tokens | Output tokens |
| --- | --- | --- | --- |
| 1 | used | 438 | 46 |
| 2 | used | 594 | 852 |
| Known total | | 1032 | 898 |

Its budget is `used=2`, `reserved=0`, `max_calls=3`; monetary cost remains
`unknown`. Thus “single dispatch” in README/comment 192 cannot describe the
model-request count. One page click / run_loop may contain multiple model
requests. These are saved records, not independent remote billing verification.

The snapshot also records one `read_document` result (70 bytes with SHA256), an
adopted 2484-byte result whose source is that tool record, and a matching
`delivered_result_id`. The saved check list contains 14 checks, including the
result ID and digest. This is meaningful limited evidence. It contains neither
the downloaded body/file nor the complete second-round assistant/tool input,
so this review cannot independently recompute the downloaded bytes or establish
that exact source body entered the later model request.

`snapshot-before-restart.json` remains the 117-byte
`unsupported_capability` response from the legacy snapshot endpoint, not a
successful same-run Core Work read. The after-snapshot is useful; the pair does
not prove before/after preservation of the original result and source bytes.
Do not invent an earlier observation to complete the pair.

The driver obtains the download link then `fetch`es its JSON in `page.evaluate`;
it does not click and inspect a browser download. Work registration and
adoption/delivery still use API calls inside `page.evaluate`; a conditional
manual `finish_attempt` fallback remains. This does not exercise U105/U106's
Core form and adoption/delivery controls, despite the file's opening comment.
These pre-existing scope gaps are not regressions caused by the 14-line fix.

## Disposition and reproduction

With the exact author Git object available and the pinned Node on PATH:

```text
python evidence/U-086/strict-download-review-probes.py 1d9ed8e9ddcaed949d38218186ede28d216dfb8f
```

Expected exit is **1** for four named assertion failures; parser/runtime errors
are not valid RED evidence. No GREEN repair is claimed: DSH retains the driver
corrections under #40, including the separate interrupted-request findings
already accepted in comment 194. Fix the download status/AU/Work comparison,
pin the original result ID/digest on successful same-run Core reads, and correct
the recorded request-count claim offline. Missing historical observations stay
unproven. New real calls require their own authorization.

This review does not approve the host connection repair implemented by this
session in PR45. Its independent engineering review is still required before
integration adoption. #22/#39/#40 real acceptance, original owners and blocked
WIP remain unchanged. This session added **zero real model calls**, performed no
service switch, and migrated no data. Standard repository verification and
private-log hashes are recorded separately in
[validation](strict-download-validation.json).

Standard checks passed: Python **792 tests, 9 skipped, zero failures** (491.741
seconds); npm check **343 frontend, 37 management and 9 action tests**, types and
build. Management render left generated files unchanged. Product and standard
test bytes equal both `902b429` and `d209a0e`; these passing checks do not repair
the four deliberately retained acceptance-counterexample failures.

Another engineering role (chatGPT-online) has explicitly taken the host review
in comment 198. Its decision is pending separately from this download review.
