# S03 acceptance driver intervention

2026-11-08. Kanban #22 comment 76 / team message 42. The foreground coordinator
continues the overdue PR #22 corrections on `codex/u067-acceptance-intervention`,
from author head `0821cff9f0744ab90e55d9178bacca0c0495b378`. DSH retains the
parent card and its unfinished real acceptance. One driver/evidence correction,
estimated 2–4 hours; no product behavior or live requests are authorized by this
document. Preserve all previous runs, including their failures and uncertainty.

- Bounded acceptance needs two distinct persisted, used model requests: an actual
  document read followed by a model call receiving that exact text/hash/size and
  paired tool ID. Download the candidate and check its identity, digest, bytes,
  source reference and the unpredictable verification token from the document.
  A one-turn candidate or a digest alone cannot pass. Check each output limit,
  aggregate usage, and the two-call bound; unknown usage is never confirmed zero.
- An explicit account must exist and have provider `opencode-go` before granting.
  The two real test classes have separate opt-ins and describe their separate
  maxima (bounded: two; interruption: one). Selecting both can use three calls.
  Previous authorization claims in evidence do not grant new calls to this run.
- Before starting interruption, retain the exact AU/Work/attempt/command tuple.
  Discover only its durable step/model request. Check returned AU and request ID,
  and scoped provider output events, before cancelling with the worker token. The
  current modeld exposes text/tool output rather than a dedicated sent event. Cancellation
  acceptance, modeld interruption and remote cancellation are distinct facts.
  Completion races and failed/mismatched lookups must not certify interruption.
- Reconciliation is tested against the product's original-request GET observation:
  completed means used with known usage and no adopted recovery body; unavailable
  or noncompleted means the original reservation remains. Reopening/replaying
  must not issue another model POST. No manual released override is accepted.
- Correct current 099/100/107 claims while retaining original logs and reported
  measurements. New offline checks cannot certify previous real runs.

Observe meaningful failing counterexamples on the unmodified helpers, then apply
the smallest corrections and validate real local HTTP/model doubles, the full
Python suite, npm check and current-head CI. This turn uses zero real model calls.
## 2026-11-08：provider usage metadata in acceptance evidence

The observer receives the full `ModeldWorkTransport.chat` usage dictionary. Core
work steps persist canonical `input_tokens` and `output_tokens`. Acceptance must
compare those two values per original request and their aggregate, while keeping
extra provider/cache/reasoning/cost metadata in the captured evidence. Extra
metadata must not cause a correct token attribution to fail, and cached tokens
must not be added to input tokens a second time. A genuine per-step token mismatch
must still fail. This correction does not increase the two-call/output limits or
turn the author's past failed real runs into successful acceptance.
