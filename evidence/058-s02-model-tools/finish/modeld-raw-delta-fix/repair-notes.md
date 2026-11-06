# S02 raw delta credential repair

This is the coordinator-assigned follow-up to `modeld-raw-delta-review.json`. It owns only `src/credential-content.ts`, `test/secret-boundaries.test.ts`, and `test/fixtures/secret-boundaries-probe.ts` under `services/modeld`. No kernel, account, usage, journal, server, Python, UI, ledger or Git mutation belongs to this task. `verified-files.json` contains exact before/after hashes and confirms the account/kernel/usage files still match the independent review snapshot.

TDD Route: Mode off / Decision strict / Authority explicit user/project instruction. Change Necessity: code-change at the existing confidentiality helper. The fixed SDK preserves raw fields that it can omit from its normalized choice/reasoning output. The prior fragment allowlist omitted real deltas; therefore normalized-output rejection alone did not establish raw-event confidentiality. No SDK or protocol contract change is required.

The baseline retained all 21 tests, including the coordinator's metadata-ID streaming fix. New actual Kernel + modeld HTTP + loopback cases reproduce six shadow paths: reasoning_text hidden by reasoning_content; Kimi summary hidden by reasoning_content; and refusal, reasoning text/summary details, and custom input in the raw unselected choice. A safe shadow control remains successful with its original events and usage.

The helper now recognizes Chat refusal/reasoning_text, the supported reasoning detail text/summary fields, custom tool input, and Responses refusal/reasoning delta. Reasoning details track only their consecutive compatible identity: type, id, index, format and signature where the pinned parser defines them. Late metadata may complete identity; conflicting identities or opaque entries end the old run. Closed prefixes are retired after scanning the frame, including runs that begin and end in the same frame. Original event payloads are never changed. Model/response IDs, function names, encrypted/data fields and other metadata remain atomic; no whole-stream cache or new model loop is introduced.

## Evidence

All commands used `<BUN>` 1.4.2 from `D:/Project/Union`. Inputs and credentials were synthetic and providers were loopback only.

| Check | Command after the pinned Bun executable | Log | Result |
| --- | --- | --- | --- |
| Baseline | `test --timeout 30000 ./services/modeld/test/secret-boundaries.test.ts` | `baseline-boundaries-20261106-153431-760.log` | 21 pass / 0 fail |
| Raw-field RED | same test command | `red-raw-deltas-20261106-153623-214.log` | 30 pass / 15 fail; six HTTP shadow failures plus missing raw continuation boundaries |
| Initial raw-field GREEN | same test command | `green-raw-deltas-20261106-153808-700.log` | 45 pass / 0 fail |
| Closed-prefix RED | same test command | `red-closed-detail-prefix-20261106-154005-223.log` | 45 pass / 2 fail |
| Same-frame closure RED | same test command | `red-detail-frame-closure-20261106-154129-379.log` | 45 pass / 3 fail |
| Final focused GREEN | same test command | `green-final-boundaries-20261106-154523-181.log` | 48 pass / 0 fail |
| All modeld regression | `test --timeout 30000` followed by the eight explicit absolute `services/modeld/test/*.test.ts` file paths | `regression-modeld-scoped-20261106-154608-297.log` | 88 pass / 0 fail |
| Isolated bundle smoke | `build ./services/modeld/src/main.ts --target bun --outfile .union/s02-finish/modeld-raw-delta-fix/modeld-build.js` | `build-smoke-20261106-154826-675.log` | exit 0, 1784 modules |

The Responses additions have direct raw-boundary tests and the existing full SDK Responses regression. The six shadow cases execute the full Chat/compatible HTTP path. Existing Go authorization/refresh, native tools, usage, grant revocation, partial cancellation, reopen and Responses behavior passed in the scoped suite.

The isolated bundle is compile evidence, not an installable candidate. Official `services/modeld/dist` was not rebuilt by this task; the coordinator must rebuild and package the final integrated source before installation or real-profile acceptance. No real model script was run or modified. Use explicit Bun test paths; a bare `test` filter can discover vendor tests.

This closes only the reported raw-delta confidentiality gap and its streaming regressions. It is not acceptance of all S02 or future protocol variants. The coordinator retains final review, whole-repository checks, browser/install and the authorized real Codex acceptance.
