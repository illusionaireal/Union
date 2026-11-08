# DSH review follow-up: loop receipts and dispatch compatibility

2026-11-08. Author: codex-home, the implementing duty session. This is a
response to Kanban messages #26/#27, **not an independent approval**. DSH
retains U-067 ownership. The review scopes are PR #24 at `39db061` plus this
addendum, and PR #25 at `4bce4919c36e2505d77da7619945ad148d0124d2`.

## PR #24

1. New rejected parent receipts include `phase: loop-stopped`. Existing
   `status`, `effect`, `turns`, tool count and usage keep their meanings:
   `effect: applied` with nonzero turns reports earlier execution; a refusal
   before any call retains `effect: none`. Successful and unknown receipts do
   not acquire this stop marker. Stored receipts remain immutable on replay.
   The current frontend consumes status/message and tolerates this additional
   JSON field; this change adds no UI action or authority.
2. `drive_loop` catches `Rejected`, with only `not_authenticated`,
   `not_authorized` and `unsupported_capability` accepted from `CoreError`.
   `OSError` propagates. Integrity errors propagate. A plain rejection after
   a durable dispatch also propagates when the original intent has no final
   receipt. The three existing fault tests continue to protect these cases.
3. `dispatch.find` searches the persisted Work steps by original command ID,
   then checks principal and full request digest. It does not filter on schema
   number. The new second-turn schema-3 test proves this with real SQLite:
   first call used, second reservation committed, second final save rejected,
   no parent terminal receipt. The next original request returns unknown with
   the first call's 11/4 tokens, one used and one reserved call, the same model
   request ID and no additional transport call. The store remains schema 3.

The contract addition preceded code. After correcting a test-fixture mistake
(the private Work record has no public `budget` projection), the unchanged
implementation produced four assertion failures for the missing phase and
five passes. Two production lines make all nine tests pass. The first failed
test run is retained as a fixture error, not another product defect. The
original three S03 probes also pass. See `review-response-verification.json`
for full validation and the retained log hashes.

## PR #25

These are source locations in the exact `4bce491` candidate. No additional
reservation or schema implementation is introduced by this response.

**One transaction.** `work_dispatch.event` sets schema 4, advances the real
version, and saves the internal succeeded event with the same `cx`.
`prepare` adds the original reservation to its transaction-local state before
calling `event`. `WorkService.run_step` exits that GovernanceStore transaction
before invoking the transport. `run_loop` similarly appends the parent intent
and calls `event` inside its AU transaction. A failure after `save` rolls back
both the marker and intent. Behavioral coverage:

- `test_committed_version_precedes_transport_and_original_facts_survive_reopen`
- `test_failed_prepare_rolls_back_marker_and_intent_before_transport`
- `test_parent_loop_preparation_alone_requires_compatible_code`

**Version checks.** The seven former `(2, 3)` acceptance sites retain their
other checks:

| Location | Boundary retained |
| --- | --- |
| `CoreAUStore.read_in` | Governance origin, audit and state validation |
| application `governance` state projection | Existing governed projection and current access |
| domain `governance.apply` | Governing authority and effective-rule checks |
| domain `governance.validate_state` | Immutable creation fields, versions and state integrity |
| domain `model_access.active` | Principal authorization, active governance and live targets |
| domain `responsibility.apply` | Existing attempt/result and responsibility rules |
| domain `work.effective` | Active governance and live targets |

Model validation formerly restricted to schema 3 is explicitly retained for
both 3 and 4 in `governance.validate_state` and `governance_store.read_in`.
The three application model checks likewise accept 3/4 while keeping their
original authorization/version rules. The new private-model-table corruption
test proves schema 4 does not skip `ModelAccessStore.validate`.
Manual `settle_step`/`reconcile_step` still reject automatic `command_id`
records independently of schema; accepting schema 4 grants no manual release.

**Code selection.** `scripts/release_package.py:check_au_schemas` reads actual
AU state and requires target schema-4 support if a Work has parent loops or
steps with `command_id`, including historical schema-3 intents. The supported
`activate`/rollback and `run` paths call `check_core_schemas` before changing
the pointer or spawning the selected code. `pack` reads the *target source's*
declared schemas instead of the packager's imported constants. Coverage:

- `test_interrupted_reservation_blocks_old_selection_and_already_selected_old_run`
- `test_pre_marker_schema_three_intent_blocks_old_code_without_read_migration`
- `test_rejected_admission_and_manual_steps_keep_prior_compatibility`
- `test_package_declares_target_source_support_without_importing_that_source`

The [PR #25 evidence](https://github.com/illusionaireal/Union/tree/4bce4919c36e2505d77da7619945ad148d0124d2/evidence/U-067/dispatch-compatibility)
also distinguishes the exact old-runtime probe from the installed-package
negative declaration control. Arbitrary old launchers cannot be retroactively
protected; schema-3 automatic data requires the updated supported entry point.

Current-head CI and a different engineering role's review still precede
adoption. This response does not certify PR #22 real acceptance, switch NAS
services, migrate live data or add real model calls.
