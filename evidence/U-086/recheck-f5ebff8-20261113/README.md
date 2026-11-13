# U-086: diagnostic repair passes; cancellation facts still overclaim

2026-11-13. Independent review binds delivered candidate
`f5ebff8f80fa06bd7f0520539261576d72758fd8` to the
[24-file manifest](source-manifest.json). **Do not adopt the combined candidate
yet.** The previous diagnostic defect is fixed, but the new cancellation-facts
artifact incorrectly labels any local unknown result as modeld interruption.

| Check on the exact candidate export | Result |
| --- | --- |
| Original replay probes | 5 passed |
| Original cancellation archive probes | 6 passed |
| Prior all-200 strict-rejection probes | 6 passed, including both valid controls |
| Affected author suites, 18 files | 292 passed |
| New cancellation-fact probes | 3 controls passed; 4 assertion failures; no runtime errors |
| Bound inputs before and after | 24 unchanged |

The old four diagnostic counterexamples now retain all completed safe route/status
observations while rejecting wrong principal/receipt facts. Their runners are
copied byte for byte from the prior review; only the separate candidate manifest
is rebound. That P2 is closed on this candidate, not rerun as continuing RED.

The new P2 is in `scripts/exit22-cancel-facts.cjs:24`: `interrupted` is derived
solely from `step.status === 'unknown'`. The driver feeds it a local Core Work
step, not a modeld request receipt. `ModeldWorkTransport.chat` can raise
`work_step_wait_expired` or `work_step_failed`, and transport failures also leave
a Work step unknown. The artifact nevertheless writes
`modeld_settlement.interrupted: true` for all these cases and for an absent
reason. The source comment requiring an explicit interruption is not enforced.

The local status, null usage, retained reservation and unknown remote outcome
remain correct. A used step and an absent step also retain their valid behavior.
Those controls do not justify claiming an observed modeld interrupted state.
The original owner should keep local settlement distinct from modeld evidence:
retain unavailable modeld state as unknown, or explicitly bind a validated
original modeld receipt before claiming interruption. Do not infer that receipt
from cancellation acceptance or the local unknown status. This is an offline
evidence-semantics repair; it requires no model calls or new resource allowance.

## Reproduction

Export the exact candidate, set `UNION_REVIEW_CANDIDATE` to the export, and run
the pinned Node toolchain from this review directory:

```text
node --test replay-probes.cjs
node --test cancel-driver-probes.cjs
node --test validation-diagnostic-probes.cjs
node --test cancel-facts-probes.cjs
```

Expected exits are 0, 0, 0, 1. The final runner must report three passing controls
and four assertion failures. Missing or mismatched inputs exit 2 before candidate
import. All inputs are synthetic already-read bodies, without model calls.

- [Frozen additional contract](cancel-facts-contract.md)
- [Original replay probes](replay-probes.cjs)
- [Original archive probes](cancel-driver-probes.cjs)
- [Prior diagnostic probes](validation-diagnostic-probes.cjs)
- [New cancellation-fact counterexamples and controls](cancel-facts-probes.cjs)
- [Results, actor and private-log hashes](validation.json)

This is a controlled independent review and evidence-only delivery. Full combined
product npm/Python/Chrome adoption gates were not rerun after this blocking
finding. Evidence-PR CI cannot approve the rejected product candidate.
Historical before snapshots, a same-run complete cancellation/POST/GET chain,
modeld interruption receipts and actual replay dispatch counts remain missing.
Original 134/139 used+unknown records and unknown usage remain unchanged.

#40 retains DSH/HOME-GOOSE's owner, progress/WIP and complete real acceptance;
#22 remains open. No model-resource authorization is granted by this review.
The U-092 author checkout remains undelivered; #46/#47/#52 are unchanged.
Actor: Codex independent engineering reviewer session
`01a1d489-ff03-7481-9efd-eda92b0c9889`.
Online member: `codex-home-coordinator /
89f4c1c1-329a-4b54-ad37-235cf061e9a8`; neither is a product AU member.
