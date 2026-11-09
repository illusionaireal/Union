# Reviewed acceptance host: integration candidate

2026-11-09. Coordinator/implementation actor: the single codex-home duty
session; online member `c18f0d21-1d63-4e37-af3e-2dbb78d75995`. Fresh Kanban
revision 607 confirmed #60 already completed and #40 still owned by DSH.
Comment 203 records this 1–2 hour integration assistance, without a new claim.

## Exact scope and independent decision

PR45 was merged into the author's branch, not into `rewrite/charter-v1`.
This candidate starts at integration `d209a0e073f2770f59787a02ca7a5ceb2f523ece`
and imports five files byte-for-byte from reviewed
`cfe0631c78c76075146b439e2dd2c4d2e4cc1c6e`:

- `scripts/exit22b_host.py` and `tests/test_exit22b_host.py`;
- the [frozen contract](host-connection-contract.md),
  [implementation history](host-connection-integrity.md), and
  [original verification](host-connection-verification.json).

The integration baseline did not contain this host. Importing its reviewed
90-line file is therefore an addition relative to integration, although PR45
was a 31-line repair relative to the author's existing host. No author driver,
evidence/127–130, product runtime, transaction, schema or model loop is imported.
The existing `ai_union/work_transport.py` blob equals the reviewed source.
The prior RED, fixture error, GREEN and incomplete acceptance records remain
unchanged; this integration does not manufacture a new RED.

The separate engineering role **chatGPT-online** approved this limited scope
in [review 5821070358](https://github.com/illusionaireal/Union/pull/45#pullrequestreview-5821070358),
bound to cfe0631, and #40 comment 199 / team message 91. That role independently
observed four failing methods and two passing controls on the original host,
then nine passing HTTP/restart regressions and two additional connection/AU
boundary checks. This implementation session does not claim those independent
runs as its own. The five imported files retain their original bytes, including
the historical wording that independent review was pending at implementation.

The host delegates to the product factory, preserving the authorized original
connection/grant IDs and revisions, model and limits. Explicit `prepare` remains
the only grant-preparation action; restart and original lookup do not prepare a
grant or dispatch a model request. The 180-second host timeout is unchanged.

## Current verification and remaining work

The exact imported host passes nine actual loopback HTTP/temporary Console
tests against this integration baseline (`tests.test_exit22b_host` and
`tests.test_work_transport_http`, 5.730 seconds). The completed full run passes
798 Python tests, with nine skips and no failures (494.718 seconds); npm passes
343 frontend, 37 management and nine action tests, types and build. Exact input
and private-log hashes are in [validation](host-integration-validation.json).
The previous incomplete Python log is retained and is not a passing run. An
initial npm launcher used a nonexistent executable; no test started in that
attempt. Running the existing npm CLI with the pinned Node passed.

PR47 was subsequently adopted at `a401d2ba3469b48b3125b749c57c21b756536bbf`,
after all 14 checks on `5948de7`; merge and tested trees match. Its six review
evidence files do not change product or standard test inputs. They are integrated
without discarding either README history. The candidate's own current-head CI
remains a separate adoption gate; neither PR47 nor this document adopts an
author acceptance driver or closes a real acceptance card.

The author retains the download and interrupt assertion corrections. The
cancelled request's own output is still required by #40; a prior step's output,
in-flight identity or cancellation delivery is not equivalent evidence. #40
comment 202 identifies the missing Core Work event observation surface as a
separate controlled engineering prerequisite. No historical missing output,
download bytes, before-restart snapshot or unknown usage is invented.

This candidate adds zero real model calls and does not run a real acceptance
driver, switch NAS business services or migrate data. #22/#39/#40 real exits
and all original owners/WIP remain unchanged.
