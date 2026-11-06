# S02 modeld independent review

Date: 2026-11-06. Reviewer: `/root/s02_feature_audit`.
Scope: working-tree credential repair described in `modeld-secrets/repair-notes.md`; specification compliance first, then implementation and evidence quality. Advisory review only; no implementation, Git, ledger, board, private profile or real model changes/calls.

**Latest status — final incremental review:** R1b is independently verified closed on helper SHA-256 `d30084fc470dce8a1c899f042f6f785321a82d2c406bedde427dc89e2717111d`. No blocking finding remains in this reviewed increment. The original findings and pre-fix assessment below are retained as dated snapshot evidence; the final closure section at the end supersedes the earlier open status.

## Findings

### R1b — Critical: omitted raw reasoning deltas can disclose the full credential

**Status:** Independently reproduced on the revised matcher (`a0d9752ab8edea444d9f817025407784d63388bc45aa4d4d954befe7cfbe4122`). This is within the same credential matcher repair. The metadata regression below is fixed, but that fix's raw field allowlist is incomplete.

- Location: `services/modeld/src/credential-content.ts:82-91`. The raw Chat continuation set omits `reasoning_text`; the pinned SDK accepts that field and chooses between concurrent reasoning fields (`vendor/opencode/packages/ai/src/protocols/openai-chat.ts:1008-1013`, `1165-1169`). Normalized events therefore cannot protect every retained raw field.
- Controlled real Kernel → pinned SDK → exact loopback comparison: a temporary copy of `secret-boundaries-probe.ts` ran only `fragmented-reasoning`, emitted the split synthetic key in `reasoning_text`, and added raw `reasoning_text` to the leak detector. With that field alone, the request was interrupted with `credential_in_model_content`, and combined public/raw events did not contain the key. Changing only each provider frame to also contain `reasoning_content: 'safe reasoning'` made the request **completed**, `error=null`, and **output_leaks=true**: the public raw fragments recombined to the full synthetic key. The SDK chose safe normalized reasoning, leaving the other supported raw delta unguarded.
- Evidence: `modeld-raw-delta-review.json` records both observations, 1.361 s / 1.330 s, one provider POST per case, zero external provider calls, exit 0, and unchanged before/after digests for all four source files. Scripts and state used isolated temporary directories and were removed.
- Required repair: cover actual supported raw delta fields before raw publication, with stream identity matching their SDK semantics. Retain the safe atomic metadata control. Adding only normalized checks or rejecting the final aggregate cannot remove credentials already written to native event history.

### R1 — Important: atomic metadata could block all safe streaming content

**Status:** Original regression independently reproduced; the specific metadata issue is now independently verified fixed. Fresh `secret-boundaries` ran 21/0, including both `cancel-safe-partial` and `cancel-safe-prefix-id`; the broader three-file recheck ran 27/0. This closes that behavior only, not R1b.

- Location on reviewed baseline: `services/modeld/src/credential-content.ts:65-75` and `services/modeld/src/kernel.ts:266-298`.
- The baseline matcher treated every string at a structural path as a continuing stream. An ordinary response ID ending in the first character of the synthetic credential left an unfinished prefix. The Kernel's global pending queue then withheld unrelated safe raw/text events until termination, even though no event contained or completed the credential.
- This is an implementation regression against the patch's documented requirement to retain streaming and preserve safe partial content while withholding only possible credential segments. A provider-selected metadata suffix can turn safe incremental output into terminal-only output.
- Isolated helper control: with synthetic credential `fixture-only-credential-738461923`, four otherwise identical safe raw/text events all published before termination for `id=completion-z`; changing only the ID to `completion-f` published zero and left all four pending. Neither case matched a complete credential.
- Real Kernel → pinned SDK → exact loopback control used a temporary copy of the existing `secret-boundaries-probe.ts`, running only `cancel-safe-partial`. Control ID `fixture-completion` gave `partial_before_cancel=true`; changing only that ID to `fixture-completion-f` gave `partial_before_cancel=false`. Both retained the partial after cancellation, retained usage and reopened events, ended interrupted with `result=null`, and dispatched exactly one loopback provider POST. Each reported zero external provider calls and exited 0. Durations were 1.855 s and 2.359 s respectively. No credential was published.
- Before and after that comparison, the four source digests matched `modeld-secrets/verified-files.json` (listed below). Temporary scripts and state were removed.
- Repair at the owner: accumulate only documented protocol/SDK delta fields, use logical stream identities rather than incidental array positions, and inspect ordinary metadata atomically. Add the metadata-only single-variable control alongside the existing split-secret and cancellation controls. A final aggregate rejection does not prove that streaming was preserved.

### R2 — Important: M07 rejection coverage remains incomplete, predating this repair

**Status:** Existing S02/modeld gap, not introduced by the credential repair; both reported cases are now independently verified fixed on Kernel SHA-256 `cac040511eed9ec6cd025f569d59ca0014d9aa9e80abf9c3f4b271dd7d1f5aa4`. Historical observations below explain the change and are not current failure claims.

- Current location at initial resumed inspection: `services/modeld/src/kernel.ts:252-257` accepts assistant public calls with an ID and function name without requiring `call.type === 'function'`. The corresponding before-image at `modeld-secrets/before/services_modeld_src_kernel.ts:245-249` has the same behavior.
- The native probe's `unsupported_tool_type` case supplied `type: custom`, yet modeld completed and made one provider POST. Unsupported public call forms should be rejected before provider dispatch.
- `green-native-usage-20261106-120152-047.log` also records `half_json` as completed with `error=null`, zero public tool calls, and an empty native part type list. The terminal guard only accepts normalized `stop`/`tool-calls`; it does not ensure a tool-call finish corresponds to a complete supported call.
- `ai_union/tool_roundtrip.py:7-17` separately requires a complete function call with the expected argument structure. Consequently, this evidence does **not** establish that the S02 core executes incomplete tool JSON; it establishes an incomplete modeld rejection boundary and misleading successful terminal classification.
- The repair author explicitly disclosed both observations. The probe's exit 0 records successful observation, not acceptance of every observed behavior.
- Repair acceptance: unsupported public call types fail before dispatch; incomplete tool JSON cannot be classified as a completed usable tool proposal; existing valid native/function call/result pairing stays intact.
- Fresh acceptance: current `kernel.ts:225-230` checks public call type and fields before either native or ordinary message lowering. `kernel.ts:320-328` guards the aggregate, publishes safe observations, rejects `tool-input-error` and tool-call finishes without a complete call, and rejects unsupported final content.
- Independent rerun of the original `.union/s02-modeld-review/native-usage-boundaries.ts` returned `half_json: interrupted/incomplete_model_result`, zero public calls; `unsupported_tool_type: interrupted/unsupported_tool_call`, zero provider POSTs. Original usage, cancellation and reopened native evidence all remained intact. HTTP 503 now correctly reported `provider_unavailable`; no external provider call occurred.
- Minimal replay from repository root: `& '<BUN>' '.union/s02-modeld-review/native-usage-boundaries.ts'`. This script's assertions cover safety controls; inspect its recorded states as well as its exit status.
- The coordinator supplied actual RED in `capabilities-red.log` and `incomplete-result-red.log`, followed by `capabilities-green.log`. Independent pinned Bun execution of `api-kernel.test.ts`, `secret-boundaries.test.ts`, and `responses.test.ts` also passed 27 tests / 62 assertions, exit 0, in 7.22 s. The updated fixture tests both public custom forms (with/without `_native`) before provider dispatch and rejected half-JSON/length output with known usage preserved.

### Terminal safe partial retention — verified, not an outstanding finding

The prior hypothesis concerning safe pending output followed by a `length` finish was addressed before independent reproduction on the old code. Current Kernel guards the aggregate then publishes safe pending events before rejecting the unusable final result (`kernel.ts:320-327`). The executed `length-prefix` control ends interrupted with `incomplete_model_result`, `result=null`, retains the `safe unfinished a` text event, and retains known usage. Do not characterize the original suspicion as an independently reproduced old-code failure.

## Pinned SDK delta field review

- Normalized `text-delta.text`, `reasoning-delta.text` and `tool-input-delta.text` are incremental and have logical IDs. `tool-input-delta.input` is a best-effort cumulative parse; `text-end.text` and `reasoning-end.text` are complete authoritative values. Treat those cumulative/complete values atomically (`schema/events.ts:165-224`).
- Chat scalar deltas include `content`, `refusal`, `reasoning_content`, `reasoning`, and `reasoning_text` (`openai-chat.ts:301-308`, `1008`, `1181-1183`). Raw `refusal` and `reasoning_text` were omitted by the inspected allowlist.
- Chat `choices[i].delta.reasoning_details[j].text` for `type=reasoning.text`, and `.summary` for `type=reasoning.summary` or `summary`, are actual incremental fields. The SDK concatenates matching adjacent types with nonconflicting identity (`id`, `index`, `format`, signature) at `openai-chat.ts:1041-1091`. Encrypted entries and their `data`/`encrypted` fields remain opaque atomic values. Array position alone is not a durable detail identity.
- Chat `tool_calls[].function.arguments` and `tool_calls[].custom.input` are accumulated (`openai-chat.ts:1196-1206`); function/custom names use the initial known value, rather than name concatenation. The raw guard must not equate SDK acceptance of custom transport with authorization to execute an unsupported public tool.
- Responses additionally handles `response.refusal.delta` and `response.reasoning.delta` in the pinned translator (`open-responses.ts:1456-1466`); both were omitted by the inspected allowlist. The source also handles the already covered output text, reasoning summary, function argument and custom input deltas. Findings are based on the fixed translator, not guessed protocol names.
- Anthropic visible text, thinking and tool `partial_json` are appended by the translator (`anthropic-messages.ts:1249-1289`). Its `signature_delta.signature` is assigned as the current signature, and `compaction_delta.content` replaces the current compaction value; these should not be assumed cumulative from the word delta alone. Gemini's normalized content IDs are lifecycle-specific; function arguments are complete objects, and a raw part array position does not itself establish a cross-frame logical stream identity. These are static semantics checks, not a claim that all Go routes received new runtime acceptance tests.

## Review basis and specification coverage

- Authority inspected: `services/modeld/AGENTS.md`, `specs/053-union-rewrite/s02-contract.md` (M02/M07/M08 and the error/usage continuation), and the supplied repair scope. The later Responses contract is coordinator-owned; its implementation is changing concurrently and is outside the initial repair's verified scope.
- Code inspected: `api-accounts.ts`, `kernel.ts`, `credential-content.ts`, `usage.ts`, secret boundary tests/fixture, the original native probe and the supplied Kernel before-image; `ai_union/tool_roundtrip.py` for the downstream acceptance distinction.
- The matcher checks actual values and decoded JSON escapes instead of relying on serialization equality. The Kernel shares one stream path and does not add provider retries or business execution. Usage is explicitly projected as `type=usage`, while SDK events retain `native_event`.
- `usage.ts` projects known, finite, nonnegative numeric fields without carrying arbitrary credential-bearing metadata. Raw/native payloads remain separate evidence. Early raw usage mapping is Chat/compatible-specific; it does not establish early usage support for every Go protocol, or establish currency/amount.
- Specification versus implementation: R1 and R2 are implementation drift in the stated boundaries, not permission to expand the product contract or change the provider protocol implicitly.

## Evidence review

Read and accepted within their named scope:

- `green-formal-boundaries-20261106-120046-965.log`: 42 passing, zero failing.
- `regression-modeld-scoped-20261106-120343-736.log`: seven explicit modeld test files, 55 passing, zero failing.
- `build-modeld-20261106-120416-724.log`: build exited 0.
- `green-review-probe-20261106-120152-054.log`: original four disclosure counterexamples have `failures=[]`, with no external provider calls.
- `green-native-usage-20261106-120152-047.log`: original native, usage, safe partial cancellation and reopen controls, with the M07 exceptions above.

Excluded: `regression-modeld-20261106-120152-047.log` was an interrupted accidental vendor test discovery, not valid regression evidence.

The additional R1 comparison is a controlled loopback observation recorded in this review, not a real-provider acceptance test. These tests do not establish actual-account integration, browser acceptance, release installation, sustained organization operation or U-072/#21 completion.

## Source snapshots and concurrent changes

HEAD at review: `d5802f8672df88db447e7e0bb86c2f1a5265ad18`, branch `rewrite/charter-v1`. Task-preexisting tracked/untracked work was preserved.

Original verified and R1-reproduced SHA-256 values:

| File | SHA-256 |
| --- | --- |
| api-accounts.ts | 08402f29813c335483b50f16e35518664a5cbbcdaff6dbacfd415e88092406bf |
| kernel.ts | b039f84ddcdfb66eb20f856b712a55dd93d84532b65194aad2ab78daab42c41f |
| credential-content.ts | 33a11869e5ed297a13013748301289c49f0a389958166c985a489174140e7cbe |
| usage.ts | 0c84b7549421fca520565eee5b516892acb202ba6765f0733073b1bdc6bfc587 |

On context resumption, api-accounts, Kernel and the matcher had changed; usage was unchanged. Initial resumed digests were `8d7242f693616b21c0073fafb3d13096e2cb61dc93c2b56c1315663b28f314d2`, `5507639b8b028de7a49b76a8ac3c1eaafaab30bd18505d7c22e7cf990ada9c75`, and `a0d9752ab8edea444d9f817025407784d63388bc45aa4d4d954befe7cfbe4122` respectively. Fresh checks must identify their actual snapshot; later edits do not inherit this review's validation.

## Outstanding bounded review work

- Recheck the coordinator's final raw delta correction against R1b, safe metadata, and the other documented supported continuation fields.
- Subsequent implementation revisions require fresh source digests and evidence; no broad Go protocol or real-provider conclusion follows from the Chat/Responses loopback checks alone.

## Assessment before the final incremental recheck

**Current credential repair ready to adopt: No while R1b remains open.** R1 metadata, the reported R2/M07 cases, and safe length termination now have passing independent evidence. Those verified fixes remain valid findings of progress; they do not cover the newly reproduced raw reasoning disclosure or certify a later source revision.

Authority note: independent engineering advice only; coordinator owns fixes, current baseline, integration, broader gates and final delivery status.

## Final incremental recheck and R1b closure — 2026-11-06

**Conclusion: R1b closed within the reviewed raw-delta repair.** The original independent disclosure no longer occurs; the new fields are checked before raw publication, and completed reasoning-detail runs release safe pending content. No new blocking implementation finding was found in this increment. Existing R1 metadata and the reported R2/M07 fixes retain their passing controls.

### Exact scope and source identity

This follow-up reviewed only the three changed files in `modeld-raw-delta-fix/verified-files.json`, their exact before-images and the new raw-field/closed-prefix evidence. It did not re-review unchanged UI or the whole repository. The fixed SDK field/identity semantics already inspected above remain the authority for continuation matching.

| File | Independently checked final SHA-256 |
| --- | --- |
| `services/modeld/src/credential-content.ts` | `d30084fc470dce8a1c899f042f6f785321a82d2c406bedde427dc89e2717111d` |
| `services/modeld/test/secret-boundaries.test.ts` | `3ea8f10eb42b8e02e63514e5789c9a2e40318710c5a4383f76ab2fcab6d03596` |
| `services/modeld/test/fixtures/secret-boundaries-probe.ts` | `d278307d0ba462f1c6577be3ded4238c38fad6f94986f38bee4d05ad2f542fb5` |

The three protected owners still matched the previous independent snapshot: Kernel `cac040511eed9ec6cd025f569d59ca0014d9aa9e80abf9c3f4b271dd7d1f5aa4`, API accounts `8d7242f693616b21c0073fafb3d13096e2cb61dc93c2b56c1315663b28f314d2`, and usage `0c84b7549421fca520565eee5b516892acb202ba6765f0733073b1bdc6bfc587`. All six hashes matched before and after independent execution; `modeld-raw-delta-rereview.json` records that comparison.

### Independent reproduction and release observations

The old fixture was loaded from the exact before-image, preserving the original probe mechanics and leak detector rather than depending only on the implementation author's new scenarios.

- **Original scalar control:** split synthetic key in `reasoning_text` alone still ended `interrupted / credential_in_model_content`, no result and `output_leaks=false`; one loopback POST, zero external calls, exit 0, 2.256 s.
- **Original failing masked case:** adding only `reasoning_content: 'safe reasoning'` now also ended `interrupted / credential_in_model_content`, no result and `output_leaks=false`; one loopback POST, zero external calls, exit 0, 1.617 s. This directly reverses the earlier `completed / output_leaks=true` observation while preserving its successful refusal control.
- **Actual stream, changed detail identity:** an unused raw choice first emitted a possible credential prefix; safe text followed while that prefix remained open. Seven polls after the prefix was queued observed no safe partial. After 120 ms, a different reasoning-detail identity closed that run; the original safe raw/text events became visible before local cancellation or the terminal stream marker. Usage, safe partials after cancellation and reopened event history were retained; no full key leaked. One loopback POST, exit 0, 2.129 s.
- **Actual stream, opaque closing entry:** the same control closed with an encrypted detail whose atomic metadata ended in the key's first character. Ten pre-close polls observed no safe partial; after closure the safe raw/text events appeared before cancellation, with usage and reopen preservation. No full key leaked. One loopback POST, exit 0, 2.234 s. The inherited fixture's `unverified_content_private=false` after closure is expected: that incomplete prefix is now a completed safe value and is released, rather than withheld forever.
- **Same-frame detection before retirement:** one raw frame contained both halves of the key in a compatible detail run and then immediately changed detail identity. A separate helper probe still returned `detected=true`; closing the run does not delete its match state before scanning the frame.

All five independent cases have `failures=[]` in `modeld-raw-delta-rereview.json`. Only synthetic keys, isolated temporary storage and exact loopback were used. Temporary scripts and storage were removed after checking the resolved temporary-directory parent and prefix.

### Review of new boundaries and regression evidence

Current `credential-content.ts:85-120` assigns compatible consecutive reasoning details to the same logical run, permits late identity metadata, and retires previous runs on a conflicting identity or opaque entry. It scans the entire raw frame before removing retired matchers (`:70-83`), including runs that begin and end in one frame. Current raw routing at `:127-141` includes the previously omitted Chat refusal/reasoning_text, supported detail text/summary, custom input and Responses refusal/reasoning deltas. Original event objects are not rewritten; function names and encrypted metadata remain atomic. The fix stays in the existing request-local confidentiality owner and introduces neither a second dispatch path nor a model loop.

Independently executed from `services/modeld` with fixed Bun 1.4.2:

```powershell
& '<BUN>' test --timeout 30000 'services\modeld\test\secret-boundaries.test.ts' 'services\modeld\test\api-kernel.test.ts'
```

Result: **49 passing, zero failing, 94 assertions**, exit 0, Bun duration 6.59 s. Complete output and command/result metadata are `modeld-raw-delta-rereview-tests.log` and `modeld-raw-delta-rereview-tests.json`.

This covers the six raw shadow scenarios and safe shadow control, eight raw-field prefix boundaries, late and conflicting detail identity, same-frame/opaque closure, atomic function/encrypted fields, original metadata/cancellation controls, and the actual SDK normal two-stage native/tool roundtrip. The API Kernel fixture also keeps M07 custom-type/half-JSON rejection and safe `length` termination with original usage. No replacement test result was inferred from a build or a probe exit alone.

The implementation's actual raw-field RED (30 pass / 15 fail), closed-prefix RED (45 pass / 3 fail), and explicit eight-file modeld regression (88 pass / zero fail) were inspected in their named logs. The 88-test result is supplied implementation evidence; this reviewer independently reran the narrower 49-test affected scope plus the five cases above. The isolated bundle smoke is compile evidence, not installation evidence.

### Closure boundary

The reviewed confidentiality increment is ready for coordinator integration on the exact hashes above. This closes the identified R1b disclosure and its new detail-run release boundary; it does not claim every future protocol variant, installable distribution, real-account operation, sustained behavior or S02/U-072 completion. The coordinator retains final integrated build/package, root checks and separately authorized real-profile acceptance. Previous UI/browser observations remain owned by their corresponding reports and acceptance runs.
