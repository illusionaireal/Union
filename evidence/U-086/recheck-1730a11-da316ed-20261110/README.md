# U-086 revised candidate review

2026-11-10. **Partial repairs verified; combined candidate not adopted.**
Reviewed `da316ed309c105694b1826be581d55857b2016d9`, which contains session
fix `1730a1161c3c59b7d4089fd9642bdbe96110754b`.

| Check | Result |
| --- | --- |
| Author session tests | 9 passed |
| Existing damaged-creation-audit control | 1 passed; 409 preserved |
| Original independent session HTTP probes | 3 passed, 1 assertion failure, 0 errors |
| Author replay tests | 8 passed |
| Revised original replay probes | 3 passed |
| Additional same-count replay probes | 2 assertion failures, 0 errors |
| Bound candidate files | 17 match Git before and after |

The legacy `Rejected(INCOMPATIBLE)` path now keeps the healthy AU accessible.
Both healthy/scoped controls pass and all observed catalog/state bytes remain
unchanged. Normal prepared V1 creation is visible in the healthy HTTP control;
it does not establish the proposed “prepared means unreadable” explanation.

The original V1 catalog-profile mismatch still returns 409 `incompatible_state`.
The path remains `session_info` creator branch → `CreationService.read` →
`resolve_directory` profile equality check → `Rejected` converted to `CoreError`.
It is not a new `read_transaction` or `_state` failure. The healthy sibling AU
cannot be listed by that failed session response. The new creator catch for
`unsupported_capability` does not affect this path.

This remaining original assertion exposes a contract decision, not permission
to swallow `incompatible_state`: the existing damaged-creation-audit test also
requires that code to surface as 409 and passes here. Before adoption, narrow
the advertised behavior to supported legacy isolation or provide an explicit
way to distinguish unavailable entries from integrity failures. Preserve the
damaged audit, locator and authorization controls. No supported creation/refresh
window or historical 117B cause has been demonstrated by these injected faults.

The replay revision fixes both earlier concrete examples: unchanged snapshots
record `dispatch_count: null` without a passing dispatch check, and an added
model-request identity leaves a failed record before strict rejection.

**P2 remains: a rejected comparison can leave a false unchanged record.** The
recorder checks only increasing counts and used budget. In two valid synthetic
cases, replacing a model-request ID at the same count or changing the content of
the same result leaves those counters unchanged. The exact driver segment
writes `status: unchanged, persistent_differences: 0`, then `compareSnapshots`
correctly rejects the changed original fact. Both assertions fail because the
durable diagnostic contradicts the rejection. The strict comparison is correct
and must remain. Record its complete outcome without fabricating either zero
differences or measured dispatches. This review does not claim an actual remote
duplicate dispatch occurred.

The original session runner is copied byte-for-byte and rebound to new Git
inputs. Replay adaptations select the revised call order, assert the new
`unchanged`/unknown-count schema, and expect no successful dispatch check. The
three original semantic checks pass before the two new counterexamples run.
Earlier files and failures remain untouched. This is bounded controlled review;
full-suite, browser, CI and real acceptance are separate adoption gates.

Inputs and runnable evidence:

- [Frozen contract](contract.md), [source binding](source-manifest.json).
- [Four original HTTP probes](session-probes.py), [HTTP result](session-result.json).
- [Five replay probes](replay-probes.cjs), [validation](validation.json).

Export the exact candidate into an isolated directory with the pinned Python
dependencies, then run:

```text
python -B session-probes.py <candidate-directory> <result.json>
UNION_REVIEW_CANDIDATE=<candidate-directory> node --test replay-probes.cjs
```

On Windows set `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, and set
`UNION_REVIEW_CANDIDATE` using the shell's environment syntax. Missing or changed
source returns exit 2 before imports; observed assertion failures return exit 1.
There are no real model calls. Private logs are retained by digest.

#40 retains HOME-GOOSE ownership and its full real cancellation/replay exits;
#22 remains incomplete. #46's 20 bound unpublished files are unchanged and its
old RED was not rerun. #61 remains review, awaiting normal user login/original
AU feedback. Engineering actor: Codex `01a1c5eb-0bf1-7082-b001-ed1e0460a9bc`;
online member: `codex-home-coordinator / 89f4c1c1-329a-4b54-ad37-235cf061e9a8`.
Neither is a product AU member. No product source, owner, NAS service, migration,
supervisor or credentials were changed.
