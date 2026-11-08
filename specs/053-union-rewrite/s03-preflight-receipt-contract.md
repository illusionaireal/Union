# S03: concurrent preflight refusal and original dispatch ownership

2026-11-08. U-067; implementation actor codex-home. Base: PR #28 at
`894f5106a105a9ab269ef9035c9a40f36e5d791c`. This freezes a bounded refinement
of [the dispatch contract](s03-dispatch-contract.md), clauses 2, 3 and 5,
before changing behavior. It follows ADR-0005; GovernanceStore remains the
single AU writer and its adopted-event rule is unchanged.

Two identical commands can both pass the first read before either commits a
reservation, because channel construction happens outside the AU transaction.
A later channel-construction failure proves only that this invocation did not
dispatch. It cannot settle another invocation's committed original request.

1. When saving a preflight refusal, check the original immutable receipt and
   committed dispatch intent in the same AU transaction as the refusal save.
2. An existing receipt wins. An existing original intent returns its step and
   model request with an unresolved intermediate response; this must not save
   a terminal refusal, release the reservation or overwrite actual facts.
3. The dispatch owner alone records the model outcome and actual usage. A
   completed call remains used; an unknown/interrupted call retains its original
   reservation and request identity through reopen, without another POST.
4. With neither original receipt nor intent, a preflight refusal stays rejected
   with effect none and no model call, reservation, or AU version change.
5. Existing request-digest/principal checks, immutable receipt replay, current
   adoption authorization, schema compatibility and legacy behavior remain.

Use deterministic events with real local SQLite and a fake transport to arrange
the two invocations before the reservation, then the refusal after dispatch.
Cover completed and unknown outcomes, completed original receipt replay, and
ordinary preflight refusal. Keep all failed evidence and run affected tests,
the original three probes, full Python and npm checks. A different engineering
role and current-head CI are required before adoption. No real model request,
new loop, NAS service switch or live-data migration is part of this candidate.
