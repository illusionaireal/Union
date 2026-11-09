# Final download session check and original cancellation recovery

2026-11-09. #40 retains DSH as owner and its real acceptance is incomplete.
This combines DSH's final-read repair `1bd324a` with PR58 `b293c626`, then
adds four permanent Node regressions. The product under `ai_union`, `web`
and `services` is byte-identical to integration `4aa020b`.

The download driver now uses the existing authenticated snapshot helper for
its last Work GET. A valid old body cannot become successful restart evidence
if the current principal/service changes or the session expires during that
read. Original result/digest/delivery, request/usage/reservation and PR58's
complete original cancellation receipt checks remain in place.

Review responsibilities remain distinct: chatGPT-online found the original
race in review5823560248; DSH implemented `1bd324a`; this codex-home session
independently reviewed those two changed files and passed all seven original
probes on the exact author archive. DSH independently reviewed codex-home's
unchanged PR58 cancellation implementation in online message101 (GET200).
No implementation session claims to approve its own authorization changes.

After the [contract](contract.md) was frozen, the new CI test ran on unchanged
PR57 `9d7fe98`: one stable control passed and three in-flight identity cases
incorrectly succeeded (three assertion failures, no runtime errors). On the
combined source, the same four tests pass, retaining the before snapshot and
rejecting final success evidence. The previous 134 related tests also pass.

Run `node --test tests/exit22-final-read.test.ts`. It executes the actual
download restart fragments and snapshot helper using synthetic GETs only.
It never executes the driver main. Two actual Chrome/Core HTTP/SQLite probes
also pass: original request/usage/budget restart (two fake turns), and original
cancel receipt restart (one fake inference/one fake cancel). Observation POSTs
are zero. Service replacement between restarts is allowed; identity changes
during an observation and substituted originals are rejected.

The old seven-case review script has one VM compatibility error on the PR58
combination: its interrupt control omits `originalCancelReference`. That
original output is preserved separately; it is not a product failure or a
successful control. Its six other cases pass. The new download regression
and the complete existing cancellation suite use compatible fixtures. The
historical review script also prints a literal old head; the validation record
binds its output to actual archive and source hashes instead.

Full validation: 808 Python tests / 11 skipped / 0 failures (499.854s);
`npm run check` passes 363 frontend / 147 Node / 37 management tests, types
and build. Render and final management consistency checks pass. Source/log
hashes are in [validation.json](validation.json).
Current-head CI is required before adoption. This scoped driver combination
targets the author's branch, not a claim that historical runs are verified.
It supplies no missing evidence139 files, page-visible real output or remotely
verified redispatch/billing proof. No real model request, production switch,
migration, supervision/configuration/agent-lock change occurred. All prior
checkout edits and its regular Git index remain untouched.
