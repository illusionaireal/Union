# U-125 browser consumer migration

2026-11-16. The new V1 shell replaces the old navigation and manual console.
Historical source/evidence is retained. No disabled or pass-through test stands
in for a missing new-page journey. U-113/U-114/U-115 retain those integration gaps.

| Previous active consumer | Current verification and limit |
| --- | --- |
| `check_console.cjs`, `check_workspace.cjs` | `u125-organization-entry-browser.cjs`: fixed login, directory, selection, scoped navigation, denial, identity, history, restart, keyboard and four widths. Legacy command behavior remains in Python/feature contracts. |
| `check_novel_company.cjs` | `tests/test_company.py` retains the separate three-cycle benchmark and HTTP/domain behavior. This is not acceptance of a novel UI in the new core shell. |
| `check_model_service.cjs`, `check_model_access.cjs`, `check_gateways.cjs` | Existing model/account/catalog/gateway HTTP/domain and model-service suites remain. Old platform account/control panels are not required core entry pages; new core model forms remain tested at their feature and resources route. |
| `u097-model-events-browser.cjs` (two variants) | Runs on `/au/:id/resources`; retains original cursor, disconnect/reconnect, restart, terminal read revocation and connection-disable assertions. |
| `u081-work-read-browser.cjs` | Work feature read/download/identity checks remain, including the migrated `work-panel-boundaries.test.tsx`. New scoped Work/result browser reading belongs to U-113/U-114. The U-125 page explicitly states this gap. |
| U-084/U-086/U-105/U-106/U-108 manual-page runners | `test_core_work.py`, `test_page_execution_http.py`, `test_work_dispatch.py` and Work registration/execution/cancellation/result/stream feature tests retain command, storage, scope, reservation, original-request and result-integrity assertions. These are not full new-page browser acceptance. |
| U-086 `page-cancel-action`, `cancel-response-body`, `registration-response-body` | Historical files unchanged; their old page scenarios leave active CI. Corresponding cancellation/registration and false-response protections remain in HTTP and rendered feature tests. |
| U-086 `observed-settlement`, `budget-conservation`, `result-provenance`, `reopened-download`, `material-read` | All five authenticated HTTP/SQLite probes remain active unchanged. |

`scripts/exit22b_page.cjs`, `exit22c_download.cjs` and exported U-108 helpers remain
because active contract tests/probes consume them. Their presence does not mount
the old UI. `node --test scripts/u108-work-events-browser.test.cjs` remains active.

The old npm aliases for legacy novel/platform/model-account browser screens are
retired. `test:browser` and `test:workspace` both invoke the new entry runner.
Python full discovery, model-service checks, offline npm checks and actual
startup verification remain required. Execution results are recorded separately;
this mapping itself does not claim the runners passed.

Governance migration keeps 53 tests: 41 exercise the actual new App/governance
route, while 12 manual responsibility tests exercise the existing scoped feature
contract. Model identity keeps all 11 cases and additionally proves old output
disappears after an AU switch. No identity, revocation, storage, version,
unknown-result or no-replay assertion was dropped to make the new shell pass.
