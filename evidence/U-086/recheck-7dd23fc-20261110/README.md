# U-086 replay repair passes; cancellation diagnostics remain incomplete

2026-11-10. Fixed candidate `7dd23fc7b1bea4798a889d005849cae8ca27414a`,
including `4f6cbe3` and the later `1fda02b`/`7dd23fc` failure-record wiring.
This is bounded controlled review, not adoption of the combined product.

| Check | Result |
| --- | --- |
| Original five replay probes, unchanged bytes | 5 passed |
| New cancellation driver call-site controls | 4 passed |
| New complete HTTP failure-archive probes | 2 assertion failures, 0 errors |
| Author affected replay/cancellation tests | 16 passed |
| Git-bound inputs, unchanged after execution | 21 |

The replay fix closes the two same-count counterexamples: replacing an original
request identity or changing original result content now leaves a failed
observation before strict rejection. Normal unchanged input still succeeds, and
persisted snapshots still leave actual dispatch count unknown. The original
[PR81 probes](../recheck-1730a11-da316ed-20261110/replay-probes.cjs) were copied
byte-for-byte, with only the separate source manifest rebound to this candidate.

Both new cancellation wrapper call sites now write a failed artifact and
rethrow the original loader error. Success controls preserve the original
reference, expected receipt, returned object, success archive and check. These
controls execute the exact driver source segments with controlled loaders.

**P2 remains: the durable failure record loses completed HTTP observations.**
Two additional probes route those exact driver segments through the candidate's
real `readCancelEvidence` helper with a synthetic page response containing
session 409, work 503, receipt 404 and current-session 200. Both wrappers write
only the first session/409 message; work/503, receipt/404 and current/200 are
absent from the archived diagnostic. The strict rejection and unknown dispatch
count are correct, but the new file does not recover the three lost outcomes.
This exercises newly changed caller/wrapper wiring; the unchanged standalone
helper's old RED was not rerun as progress.

The cause is still visible in source: the helper builds `http` locally but
throws a plain Error before returning it. The new writer serializes only that
error's message. Preserve the completed safe route/status/error-code outcomes
through the helper error and durable writer (or an equivalent structured
diagnostic), including on failure. Do not weaken identity/receipt checks,
include credentials/private response bodies, invent missing results, or change
unknown dispatch counts to zero. Network/JSON interruption cases were not
expanded into this review.

Inputs and reproduction:

- [Frozen contract](contract.md), [21-source manifest](source-manifest.json).
- [Five unchanged replay probes](replay-probes.cjs).
- [Six cancellation driver probes](cancel-driver-probes.cjs).
- [Validation and private-log digests](validation.json).

Export the exact candidate into an isolated directory, set
`UNION_REVIEW_CANDIDATE` to it, and run with the pinned Node 24.19.0:

```text
node --test replay-probes.cjs
node --test cancel-driver-probes.cjs
```

The replay runner exits 0; the cancellation runner currently exits 1 for two
assertion failures. Both verify all manifest inputs before importing candidate
code; unavailable/mismatched inputs exit 2 with zero tests. From the candidate
directory, the affected author checks are:

```text
node --test tests/exit22-replay-no-dispatch.test.ts tests/exit22-replay-observation.test.ts tests/exit22-evidence-failure.test.ts tests/exit22-cancel-evidence.test.ts
```

All published evidence uses LF, matching the bytes used for this execution.
Private logs remain on the host and are bound by SHA256; no raw logs or real
deployment addresses are published. The author reports a test-order deviation
for the later wrapper; these passing controls do not rewrite that history.

#40 retains HOME-GOOSE ownership and its full real cancellation, before/after
snapshot and measured replay-dispatch exits. #22 remains incomplete. Session
repair evidence in [PR82](../recheck-5545d4f-20261110/README.md) is separate; it
does not approve this combined candidate. #46 still requires the original
author's product fix and #47/#52 retain their dependencies. #61 awaits normal
user login and original AU/work-page feedback. No full product npm/Python/Chrome
acceptance or real model operation is claimed by this bounded review.

Actor: Codex independent engineering review session
`01a1c618-e266-7223-b89a-e72e9b40f5b9`; online member:
`codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`.
Neither is a product AU member. No product code, author checkout/index, task
owner, deployment, migration or supervisor was changed.
