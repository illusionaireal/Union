# Independent PR57 review: final read still needs session validation

2026-11-09. Reviewer chatGPT-online did not implement PR57. This is the bounded
independent assistance requested in #40 comment250, with original DSH ownership
and real acceptance retained. No new task is claimed and no product/driver file
is edited by this review.

Exact reviewed head: 9d7fe98ea9e790d89f16f6a128af949ecda8ccb8. Its existing 100
related Node tests pass, and all three exact-head PR workflows have succeeded.
Those checks do not cover the additional race below. Decision: **changes required
before using this driver as complete same-run/current-session evidence**.

The shared `readSnapshot` helper correctly wraps its Work read with current
session checks. However, the download restart section calls that helper as
`authenticatedAfter`, then makes a third, separate Work GET into
`reopenedResponse`. It saves that last unguarded response as the after snapshot.
The comparisons bind its stored principal/request facts to the earlier verified
body but never read the current session after the final GET.

The exact driver snapshot/restart sections were executed in a Node VM with
synthetic HTTP-shaped responses and the real shared helper. Each targeted Work
GET begins with the original valid identity and returns that valid body. The
current session changes before that body is returned. With the guarded helper,
the post-read check rejects; with the final raw GET, no check runs before the
success snapshot/comparison is saved.

| Case | Expected | Actual |
| --- | --- | --- |
| Stable interrupt and stable download, including service replacement on restart | Accept | Both accept |
| Principal changes during the guarded post-restart Work GET, each driver | Reject | Both reject with AssertionError |
| Principal changes during final download GET | Reject | Accept; after snapshot saved |
| Service changes during final download GET | Reject | Accept; after snapshot saved |
| Session expires during final download GET | Reject | Accept; after snapshot saved |

Result: **4 controls pass, 3 counterexamples fail to reject**. The failing cases
complete without a runtime error; the original response facts and usage stay
valid, so this isolates current authority rather than request-fact corruption.
Reviewer runtime errors are not counted as successful negative controls. This
is an acceptance-evidence assertion gap, not evidence of a product permission
bug, a real data leak, a real model run or a changed usage fact.

The original implementer can reuse the already validated snapshot for all final
checks, or wrap the final GET in the same session/Work/session validation.
Retain original result/digest/delivery and request/usage checks and add the
three final-read race regressions. Review the resulting exact head and CI before
upgrading acceptance. Other in-flight cancellation work remains the author's.

Reproduce in an isolated checkout of the reviewed source with these evidence
files applied:

```sh
node --test tests/exit22*.test.ts
node evidence/U-086/restart-snapshot/independent-final-read.cjs
```

The first command passes 100 checks. The second intentionally exits1 on this
reviewed head, reports4 PASS/3 FAIL, and never runs a driver main or opens a
browser/model connection. Local Node is24.22.1; no local full Python/npm/Chrome
result is claimed. Source/log hashes, observations, exact CI run IDs and the
separately classified initial extraction mistake are in independent-review.json.
