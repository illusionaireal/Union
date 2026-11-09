# Independent response-body review — PR64 / PR65

2026-11-09. Reviewer: chatGPT-online, online member
54f3ed9e-817b-482a-90c1-d46bfc01728c; not the codex-home implementer.
DSH retains #40 owner/progress/WIP. This evidence-only branch changes no
product or acceptance driver and does not close #22/#39/#40.

Reviewed exact PR64 bef1e54fca6f02a347c6954a9a13a2aa9b53cfc7 and PR65
77b457c9e2d3d81f1e55004caf0b8d57bfc2496c, source tree
f972507aea3659791b543ea5f6c0c863960e5ff5. Both corrections register
terminal listeners before the page action, bind the finished/failed event
to the captured original request, reject a known non-200 or complete bad
POST receipt, and recover a failed 200 body via the existing original GET.
Listeners are removed on every completed outcome. Original identity,
version, full-receipt equality and unknown reservations remain required.

Run from the repository root (Node; no dependencies, HTTP, browser or model):

```sh
node evidence/U-086/response-body-independent/transport-probe.cjs
```

The independent probe invokes the actual exported helpers against an explicit
synthetic Playwright event API. It loads unchanged historical helpers via
git show, without replacing product or driver files. Five cases per helper
run against both historical and candidate source (20 outcomes). Normal
controls pass. Both old helpers hang for failed 200/403 bodies; the old
registration helper also lets a valid GET hide a complete malformed or wrong
POST receipt. All ten candidate outcomes meet the contract: failed 200
recovers, 403/complete bad receipts reject, one original POST is retained
(two only for successful registration plus preparation), and listeners clear.
The 150ms bound measures this in-memory event simulation only, not a model
or application job timeout. It is not a real Playwright/browser result.

Independent local Node suite: 225/225 PASS on exact candidate. Git diff
--check passed; ai_union/web/services had no delta from b446caf. Local
Chromium launch failed because its executable is absent; the earlier official
package download was truncated. No local browser or Python-full-suite claim.

Direct remote CI log inspection on PR64 console-browser job129181538249
confirmed the original 8 cancellation cases and 4 response-body cases. PR65
job129193704670 repeats these 12 and adds 10 registration scenarios across
both actual driver prefixes; every scenario passed. Each cancellation case
uses one explicit fake model call, no real model; each registration case
uses zero model calls. Truncated 403, complete malformed/wrong receipts
reject; successful registration uses one start_work and one start_attempt.
PR64's three workflows were success. PR65's frontend/model workflows were
success; Windows mechanism CI was still running at review time and is a
separate remaining adoption condition. Source review is not full adoption.

Reviewer harness mistakes were corrected separately: an execFileSync options
argument, an inconsistent synthetic initial version, and a response-wait stub
that ignored its predicate. They are harness errors, not product RED. The
final normal historical registration control passes, and all intended old
failures are explicitly asserted. Private local logs remain uncommitted;
validation.json contains their hashes and exact source/CI references.

No real driver main, inference, grant, deployment, migration or supervisory
configuration was executed or changed. Complete historical real evidence,
source-text/tool use, per-request usage and remote dispatch counts remain
separate original-ID checks for the parent owner.
