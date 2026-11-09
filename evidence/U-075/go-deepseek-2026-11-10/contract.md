# U-075 / UNI-028: selected Go model acceptance

Frozen before execution, 2026-11-10. Implementation actor:
Codex/developer/session-01a1c217-f4aa-78e3-830b-173a7b72e707.
Online member: codex-home / c18f0d21-1d63-4e37-af3e-2dbb78d75995.
Baseline: f2fb72c2b31b2e2c29ea385d8ea1da05506fee3f.

The user explicitly selected OpenCode Go `deepseek-v4.1-flash` and authorized
its subscription calls without a call-count limit. Each isolated acceptance AU
still receives an explicit bounded resource grant. Initial batch: at most six
calls, 2048 output tokens per call, synthetic public material only. Additional
batches require a recorded engineering reason and preserve earlier requests.
Provider-reported unknown usage or cost remains unknown, never zero.

The provider's official Go catalogue advertises this model through Chat
Completions. This run uses the existing `openai_compatible` core profile and
the real pinned modeld kernel. It cannot establish Responses, OAuth, other
models, remote cancellation, live input, or continuous business support.
Existing Responses child-card obligations remain separately visible.

## Required observations

1. Start an isolated core and modeld from the stated source/build. Register and
   log in through core HTTP; create one prepared AU, adopt its local governance,
   explicitly authorize `read_document`, save the selected connection and grant
   the batch. No existing business databases or credentials are migrated.
2. Saving makes no inference. One normal check calls the actual selected model,
   reads the selected document through the core tool boundary and calls the
   model again. Verify the original material hash, paired tool receipt, native
   context and challenge in the final reply. The challenge and document body
   must not occur in the first request. Persist request/Work/Member/Mandate/
   Agent-definition identities and original per-attempt usage.
3. Observe persisted output through the scoped V1 event projection. For a
   separate cancellation check, issue cancellation only after an original
   request has produced an actual text delta. Record a race with completed
   output as such; it does not pass the interrupted-request case.
4. Keep local stop acceptance, modeld interrupted/completed state and remote
   provider certainty separate. Unknown dispatched work retains its reservation
   and responsibility. Never claim a local abort refunded or remotely cancelled
   the provider request.
5. Stop and restart the isolated processes with the same data. Log in normally,
   query the original checks/requests/events and verify identity, output and
   reservation continuity. Observation and original-request reconciliation must
   not create a new provider request or replay an already dispatched attempt.
6. Use the real React workspace to read the actual persisted results, usage,
   stream and recovery status. The page must expose unsupported capabilities
   honestly. This does not require or imply implementing the pending S06 input
   contract in a second scheduler.

The driver saves dispatch intent before a side-effecting command and records
its receipt separately. A lost response is queried by its original command ID;
the entire run is never silently restarted. Private roots, authentication,
provider inputs/outputs and databases stay outside Git. Public evidence contains
only explicit source/build identity, sanitized observations, hashes, counts and
limitations. Actual failed attempts and setup failures are retained.

No product change is assumed. A discovered behavior defect requires a meaningful
RED before the minimum fix. Engineering checks, this real selected-profile run,
independent review, deployment and sustained operation are distinct gates.

After the actual acceptance passes, update only the existing Chat profile's
streaming/cancel evidence declarations with the selected provider/model and
the unknown remote-cancellation/usage limits. Keep Responses and modeld-grant
claims controlled and live input unsupported. This is evidence data, verified
by the existing profile/HTTP consistency checks and the actual browser.
