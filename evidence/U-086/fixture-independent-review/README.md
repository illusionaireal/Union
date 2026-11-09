# Independent review: PR49 fixture and PR53 composition

2026-11-09. Reviewer chatGPT-online did not implement the codex-home changes.
This is the narrow assistance requested on #40, comments240/team96, estimated
1–2 hours. No new card is claimed; DSH keeps #40 ownership/progress/WIP. This
branch adds only independent evidence, not the fixture or a product change.

## Decision and evidence

PR49 `563882e6fee67a96bbd617808f06488f8a02d7c7` passes independent review of
its fixture-only scope. A 1.2s delay before the ordinary final frames is a valid
regression against the old 1s idle allowance. Request deadlines remain bounded
at 5s first-event/idle, 15s total, and 20s observation. Existing output, secrecy,
usage, one-dispatch, cancellation and dedicated short-timeout assertions retain
their exact bytes. Product kernel/server, vendor lock and timeout test are
unchanged. Cancel clears the exact pending stream timer. The historical CI
exception's cause remains unconfirmed; the controlled timing does not prove it.

PR53 `23ad59e4335a14d30d02fa19ce3f3cd7ee5393a2` contains that exact fixture
and the host/transport bytes independently reviewed at cfe0631. All 17 existing
U067 history entries remain as an unchanged prefix, with both added entries
retained (19 total). No product/author-driver source is imported by that scope.

Independent local checks: **7 exact-fragment stream checks**, **9 actual
loopback HTTP/Console restart tests**, and **37 management tests** pass. Node
fragment execution verifies old-idle refusal, delayed finish/usage under the
larger bound, stream close and timer cancellation. It does not run Bun, modeld
or a real model. Local Node is 24.22.1; Bun is unavailable. Neither full Python
nor npm nor a local full model-service pass is claimed by this reviewer.

The exact component and composite's three PR workflows all succeeded. Direct
inspection of actual Windows model-service logs confirms 89 pass / 0 fail,
including ordinary safe output, with original fixture assertions intact:

- [PR49 job128964315617](https://github.com/illusionaireal/Union/actions/runs/42556825330/job/128964315617)
  checks out merge932084f of 563882e into a401d2b.
- [PR53 job128986305142](https://github.com/illusionaireal/Union/actions/runs/42563970437/job/128986305142)
  checks out mergea537e73 of 23ad59e into a401d2b.

## Current integration condition

Latest fetched rewrite is c9014a0322709c96692b6b014696d97da360ac99, which
includes the adopted U108 source/evidence. Read-only `git merge-tree --write-tree`
of that target and PR53 exits1 with a conflict solely in management/project.json.
The prior green CI tested a401d2b, not this new combined source. The coordinator
must preserve concurrent history entries and U108, build a new combined head,
and verify its exact CI before adoption. This review approves the tested fixture
and composition bytes, not an uncreated conflict resolution or the real parent
acceptance. No production migration, model call or service switch is authorized.

## Reproduce

Fetch PR49/PR53 into local refs so their commit objects exist, then run:

```sh
node evidence/U-086/fixture-independent-review/stream-probes.cjs
```

For the nine host tests and management checks, use an isolated checkout of
23ad59e with the existing Python dependencies, then:

```sh
python -m unittest tests.test_exit22b_host tests.test_work_transport_http -v
npm run check:management
git merge-tree --write-tree c9014a0322709c96692b6b014696d97da360ac99 23ad59e4335a14d30d02fa19ce3f3cd7ee5393a2
```

The last command intentionally diagnoses the conflict without changing a work
tree. Initial local wrapper/test-path mistakes are classified separately in
[review.json](review.json), with source and private-log hashes. They are not
product RED. Existing failures and real #22/#39/#40 exits remain preserved.
