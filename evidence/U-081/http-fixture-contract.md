# Slow loopback fixture response contract

2026-11-08, frozen before the fixture change. Follow-up to U-081/#35 review,
PR #26 at `6b50769e33b85172289b3badd6faf361a588ec19`.

Windows CI job `128680865622` failed while creating a fixture AU in
`RuntimeHTTPTests.setUp`, before its session-identity/privacy assertions. The
shared functional HTTP helper times out after four seconds. The same-head
second Windows run passed. This is distinct from PR #25's `join_jobs` failure.

The shared test helper uses a 30-second socket timeout for loopback responses.
This is the socket's blocking-operation timeout, not an end-to-end deadline.
It still sends the original request exactly once, returns the original status
and content, and closes the connection on success or failure. It must not
retry a POST or accept a missing/late result as success. Explicit product/model
deadline tests, product timeouts and CI job limits remain unchanged.

RED/GREEN probe: delay handling the fixture's original create command for 4.5
seconds, then execute the real Console creation and return its real response.
The old helper must raise TimeoutError. The candidate must receive the saved
original receipt and AU with exactly one command invocation. This injected
fixture delay does not modify or disable normal product code.

Validation: the delayed HTTP probe; full HTTP and runtime observation suites;
full Python and npm checks on the candidate; current-head protected CI before
integration. No real model service or deployment is involved.
