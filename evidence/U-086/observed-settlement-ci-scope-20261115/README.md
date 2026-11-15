# U086: restore the settlement browser fixture boundary

2026-11-15. The observed-settlement browser probe dynamically extracted the
cancellation driver through `const restartComparison`. The author's new inline
strict comparison appeared before that marker, so the fixture began validating
a full snapshot it was never designed to construct. Its legitimate unknown
control failed with `explicit request usage, including null`.

The repair changes only the fixture's end marker. It still executes the original
settlement and restart assertions, then independently reads the original cancel
receipt and compares actual SQLite steps and budget. The unknown control and
both released rejection controls pass; browser reads issue no writes. Production
snapshot validation and replay recording are unchanged, and no usage is invented.
The subsequent full-snapshot/browser suites pass 7 + 10 + 11 + 10 scenarios.
Full checks pass: npm (359 Node, 363 frontend, 37 management) and Python
857 tests / 9 skipped / zero failures in 556.443 seconds after dependency repair.

[Contract](contract.md) and behavioral RED were recorded by predecessor actor
`01a1df41-8ec2-7722-a4eb-bd7ebe729e94` before its edit. This run continues that
repair as an implementer, not its independent approver. The exact RED input was
`3a4fecb1c072d51d4748234191e390297c1a1a22`; current parent
`9798bc0b477a9a458d2f89bba52576ebb83483fe` changes only the author's PR description.
The input export was checked against all 2,405 ordinary tracked files before
verification. The predecessor's four independent candidate probes passed
5 + 6 + 6 + 7; their 24 bound input files are unchanged at the current parent.
That closes the prior local-unknown/interrupted finding only on the bound input.
It does not approve every part of the author's combined candidate.

[Validation](validation.json) records actual results and private log hashes.
The [byte check](repair-byte-check.json) confirms all original scenario assertion
bytes remain unchanged.
The initial missing frontend build, absent SDK dependency and Windows dependency
path-length failures remain recorded as environment failures. Successful results
are reported separately. Original source, failed CI and prior review evidence
remain available; no shared checkout/index or dirty vendor was overwritten.

This is a narrow test-maintenance PR based on the author's delivered branch.
It needs the author's non-implementer review and exact-head CI before adoption.
Full combined-product integration and #40's real acceptance remain separate.
No product source, accounting, authority, schema, deployment, migration or real
model invocation changed. DSH retains #40 owner/progress/WIP and #22 stays open.

Implementation actor: Codex duty continuation, session
`01a1df4f-5b39-7153-b26c-fb4880864505`, run `20261115T130441808723Z`.
Online member: `codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`.
Both are engineering identities, not product AU members.
