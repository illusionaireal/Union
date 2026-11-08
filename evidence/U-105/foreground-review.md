# U-105 foreground review and CI observation follow-up

The foreground coordinator independently reviewed the scheduled implementation
at `0a86b6f270d88373b46ccd934ff00b38cd757dca`. This is a separate engineering
run from the feature implementation. The online member is
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`; neither run is a product AU member.

[Review 5819080040](https://github.com/illusionaireal/Union/pull/38#pullrequestreview-5819080040)
approves the controlled product scope subject to final current-head checks.
The reviewer independently reproduced four late-POST access/scope failures
on unchanged `948d8c3`, then verified the published fix. Four authored and
three additional actual HTTP/SQLite probes, 59 relevant DOM checks, and 17
actual Chrome checks passed. Each browser scenario kept one original Work
POST and zero model requests. The three additional HTTP probes are runnable
with `python evidence/U-105/independent_probe.py .`.

Reviewed UI and browser fixture contents match the published source. Product
Python is unchanged from `bb5795b`; current identity/authorization and original
request checks remain on the existing Work/Member/Binding/Definition/Mandate
transaction. The foreground follow-up changes only a test and this evidence.

Windows job 128815352021 at the earlier head failed in the six-request legacy
scenario: `Console.join_jobs()` exhausted its fixed ten-second wait. The job
ran 773 tests in 693.510 seconds, with one error and ten skips. In an isolated
source archive, six local responses delayed by two seconds each reproduced
the same error without changing product code or exceeding each request's
configured three-second timeout. This is not evidence of the specific source
of every delay on the hosted runner.

The scenario now observes the existing worker for at most 30 seconds before
calling the original `join_jobs()`. Its assertions still require six actual
HTTP requests, three artifacts, persistent execution history and the explicit
simulated verdict. The delayed six-request probe passes, as do all 27 model
API tests. Product request deadlines, `join_jobs()` and graceful close are
unchanged. The original CI and local failures remain recorded.

Hashes, scope and the independent review are in
[foreground-review.json](foreground-review.json). Raw local logs remain
host-private. Final npm, Python and current-head CI results and the actual
merge SHA must be recorded on PR38 before completing #59. #60, real #39/#40,
parent #22 and sustained operation are not completed by this evidence.
