# U-086 session resolution repair independently verified

2026-11-10. Candidate `5545d4f8ab36f2b94900630a4b41e863cfaecbe3` repairs the remaining original session/catalog counterexample. This is a bounded controlled review, not product adoption.

| Check | Observed result |
| --- | --- |
| Original independent HTTP probes, unchanged | 4 passed, 0 failures/errors |
| Author session/real-catalog plus creation-failure/catalog-integrity regressions | 36 run: 35 passed, 1 platform skip, 0 failures/errors |
| Candidate inputs bound to Git and unchanged after execution | 21 |
| Previous reviewed inputs unchanged | 15 of 17; only creation service and Console changed |

Healthy Core/legacy and scoped session controls remain successful. Both legacy and Core profile-mismatch fixtures now return 200 without admitting the inconsistent row; all four observed catalog/state snapshots remain unchanged. The existing damaged-creation-adoption control still rejects with 409. The author's new real HTTP test also verifies that direct access to the unresolved AU remains 409. It is one test with two response assertions, not two independently run test cases.

The implementation distinguishes resolver rejection from the Core store's audit rejection before the session listing handles it. `CoreError` inherits `Rejected`; the audit store's specific incompatibility message is preserved as a failure, while resolution incompatibility is explicitly classified for listing omission. Catalog shutdown integrity checks remain active. This validates these concrete paths; it does not establish a creation/refresh timing defect or the cause of historical run 117B.

Replay driver/recorder/comparison inputs are unchanged from the preceding [review](../recheck-1730a11-da316ed-20261110/README.md), so the two same-count replay-diagnostic findings remain open. Cancellation diagnostic code also has no changes in this candidate; its earlier failure-record finding remains open. Those historical RED checks were not rerun. Full product npm/Python/Chrome and product adoption were not claimed for this bounded session review. #40 retains its owner and full real cancellation/replay acceptance; #22 remains incomplete.

- [Frozen contract](contract.md) and [Git input manifest](source-manifest.json).
- [Unchanged four HTTP probes](session-probes.py), [observed HTTP results](session-result.json), and [validation/log digests](validation.json).

Export the exact candidate into an isolated directory and use the pinned project Python dependencies:

```text
python -B session-probes.py <candidate-directory> <result.json>
python -B -m unittest -v tests.test_core_session_inconsistent_catalog tests.test_core_session_real_catalog tests.test_core_creation_failures tests.test_catalog_integrity
```

Run the second command from the candidate directory. On Windows set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`. Missing or mismatched probe inputs return exit 2 before imports. The executed source manifest used CRLF. Its original digest remains in the execution records; the published LF digest is recorded separately in validation. [Publication binding](publication-binding.json) verifies the exact CRLF-to-LF transformation and unchanged JSON facts, including the original HTTP result. The initial whitespace preflight blocked publication before any push; only line endings were normalized, without rerunning behavior. Private execution logs are retained by digest.

Actor: Codex independent reviewer `01a1c602-13a4-78c3-b56a-154670a13d0a`; online engineering member: `codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`. Neither is a product AU member. No product code, author checkout, task owner, real model call, deployment, migration or supervisor was changed. U092's 20 unpublished inputs were unchanged and not retested; #61 remains awaiting normal-login/original-AU user feedback.
