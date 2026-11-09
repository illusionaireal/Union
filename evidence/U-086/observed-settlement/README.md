# U086: do not accept release of an observed model call

2026-11-09; #40 comment278. The interrupt driver accepted `released` after
its original-output gate had already observed text from that same request.
Two consistently wrong before/after snapshots therefore passed even with
the reservation reduced to zero. This is an acceptance false positive;
these tests do not demonstrate that the product itself releases such calls.

The [contract](contract.md) was frozen before edits. The implementation changes
only two assertions in `scripts/exit22b_page.cjs`: the observed request must
remain `unknown` or `used`, including after restart. Unknown keeps its original
reservation. Completed calls with unreported usage keep null, and unrelated
unexecuted steps can still be released. Product accounting, authorization,
transactions, public projections and deadlines are unchanged.

The exact author input was `77b457c9e2d3d81f1e55004caf0b8d57bfc2496c`.
The task also preserves the later three-file independent-review input
`fce8264a621f3bdb90c0bedcfb333d413e023c9e`, which changes no implementation.
The publication parent is `c1ff90b80485e0300dc6b07b01a97179b663c9ab`,
whose tree equals fce8264a after merging PR65 history. Integration remained `4aa020bf6e528d1d9bc6ab28c5aa8b63cc53fe5c` at readback.

- Eight Node tests execute the original output gate, original cancel GET,
  settlement, rebuilt-state checks and snapshot comparison. The unchanged
  driver passed six controls and failed two expected-rejection cases. After
  the minimal edit all eight pass; no real driver main is imported.
- The [Chrome probe](browser.cjs) exercises the original settlement and
  rebuilt-state assertions through real Core HTTP/SQLite, with one explicit
  fake call and fake cancellation per scenario. The actual unknown control
  passes; two response faults replacing its status with released were accepted
  by the original driver and are now rejected. The test does not mutate SQLite.
  Restart and original cancel GET preserve the actual step and budget; these
  evidence reads issue no POST. This probe does not claim real output timing.
- This browser fixture uses the older single-step path, whose unknown step
  omits usage. It therefore exercises the targeted driver assertions and
  separately verifies actual original steps/budget, not the generic snapshot
  validator. The Node suite covers that validator with explicit null usage;
  the existing full-loop snapshot coverage remains unchanged.
- Initial Node fixture cursor/diagnostic matching errors, the first browser
  fixture's missing-usage mismatch and an overbroad stale-attempt comparison
  are retained as test construction failures, not behavioral RED. The final
  pre-edit browser run is one passing control and two actual false positives.
  Source and private-log hashes, counts and full checks are in
  [validation.json](validation.json).

Final checks: canonical LF npm passes 233 Node, 363 frontend and 37 management
tests, types and build; the canonical browser passes all three scenarios.
Full Python passes 808 tests / 10 skipped / zero failures in 513.067 seconds,
with Bun 1.4.2 explicitly enabled. All Python and product implementation bytes
remain unchanged. Six dedicated browser runs, including fixture failures,
made 18 fake calls and 18 fake cancels; real calls remain zero.

The implementation actor is the single codex-home duty session, online member
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`. DSH retains #40 and its WIP/history.
Twenty pre-existing files, the normal index and dirty vendor remain unchanged;
verification uses a Git source export and an isolated task index in the same
repository. The original synchronized checkout is untouched.

PR65 was separately merged into its upstream candidate branch after exact
head CI and independent review5826784677; that is not rewrite adoption of the
author's combined driver. This new change still needs its own independent
engineering review and exact-head CI. No new real inference, grant, business
deployment, migration, supervision, configuration or lock change occurred.
#60 remains done; #22/#39/#40 real exits and historical failures remain open.
