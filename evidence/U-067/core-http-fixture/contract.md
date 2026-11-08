# V1 HTTP fixture wait contract

2026-11-08, frozen before changing the helper. Actor: codex-home; online
member `c18f0d21-1d63-4e37-af3e-2dbb78d75995`. Kanban #22 comment #68;
DSH retains the parent card. Base: PR #28 at
`4494b758348312f71d37d00e4db7e99fd92fdaab`.

Windows CI job [128721896081](https://github.com/illusionaireal/Union/actions/runs/42477468161/job/128721896081)
failed in `ResponsibilityTests.setUp`, while the V1 HTTP helper waited for
fixture AU creation. It reached its five-second socket timeout before the
responsibility assertions. The separate legacy HTTP helper already has the
reviewed PR #27 repair and is unchanged.

`CoreCreationTests.request` defaults to a bounded 30-second socket wait for
functional fixture calls. Explicit caller timeouts still override the default.
This is a socket blocking-operation timeout, not an end-to-end deadline. The
helper sends each original POST once, returns its real status/body/cookie,
propagates timeouts, and closes the connection in either case. A timeout does
not imply that the original creation did not commit; recovery reads its saved
receipt without another POST.

The RED probe delays the real V1 creation command by 5.5 seconds. The unchanged
helper must time out; the candidate must return the original successful receipt
and exactly one persisted AU from one command invocation. A second probe uses
an explicit short timeout and checks that it still raises, while the same
original creation finishes and can be queried without retrying it. No normal
product code is disabled to create the delay.

Scope: this helper, the executable probe and evidence. Product deadlines,
authorization/identity assertions, CI limits, DSH's real acceptance drivers and
the reviewed legacy fixture remain unchanged. Run the probe, affected creation
and responsibility suites, full Python/npm checks and the original three S03
probes. Adoption still needs current-head CI and the outstanding independent
reviews of PR #24/#25 and the combination. No real model calls or deployment.
