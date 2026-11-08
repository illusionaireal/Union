# 2026-11-09 Windows validation follow-up

The PR36 source `ce10e343dd586aaf323edbc68262bf0a1cd89d72` was not
adopted after two Windows checks failed. Job 128794315356 completed 768
tests in 652.087 seconds with one failure: the old transport deadline test
measured 3.156 seconds against an end-to-end 1.8-second assertion. Job
128794299847 was cancelled at the workflow's 15-minute limit. Neither
failure is erased or represented as a pass.

The unchanged product reproduced the first failure locally by delaying
only `Console.receipt` reads by two seconds: one assertion failed at
3.234 seconds while the request correctly became unknown. The public
receipt includes persistence and read work outside the transport deadline.
This isolates a false positive in the test; it does not establish the
specific source of every millisecond on the hosted runner.

The test now holds an actual local HTTP response behind an event. It
requires local completion while the provider remains blocked, an unknown
receipt, the original reservation, rejection of another probe, one original
POST and no result file. Cleanup releases the provider. Bounded event waits
protect the test process; they are not product timeout changes. The same
slow-receipt probe passes, as do all 27 model API tests. No product code or
authorization changed. CI's job cap is now 25 minutes to accommodate
installation, the full suite and the fresh CLI validation; no check is
skipped and the failed runs remain available.

Before this test-only increment, combined source `57c5297` passed 769 local
Python tests (9 skipped, 499.224 seconds), all 261 frontend tests and npm
checks. Independent review of its readable-request repair is
[5818752520](https://github.com/illusionaireal/Union/pull/37#pullrequestreview-5818752520);
the separate observation review remains
[5818722576](https://github.com/illusionaireal/Union/pull/36#pullrequestreview-5818722576).
Product source bytes are unchanged by this increment. Final current-head
checks and the actual adoption SHA must be recorded on PR37 before either
engineering child is completed. PR37 preserves PR34/35/36 ancestry and is
the combined adoption candidate; the failed PR36 head is not merged first.

Local raw logs stay host-private; hashes are in
[ci-deadline-followup.json](ci-deadline-followup.json). This is controlled
engineering evidence, with zero new real model calls and no migration or
business deployment. Parent #22/#28 and their real acceptance remain open.
