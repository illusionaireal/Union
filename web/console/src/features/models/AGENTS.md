# S02 core model access frontend owner

- Own the `core.models.v1` React flow in `specs/053-union-rewrite/s02-contract.md`: separate saving, bounded authorization, document tool checks and default adoption. A command receipt records acceptance, not model execution success.
- Reuse the workspace, authenticated same-origin client and native form/dialog patterns. Core governors need no platform administrator role; the server remains authoritative for permissions and current versions.
- Bind reads, previews, submissions and late responses to principal, service instance and AU. Session renewal for the same principal preserves inputs and focus; identity, instance or read-access changes erase the old content.
- Keep keys only in form/request memory and clear them on submission or scope change. Editing an API connection requires a new key. Never store document bodies, keys or native model data in browser storage.
- Persist original request references and non-secret target IDs only. Unknown requests use original receipt lookup; explicit reconciliation may continue undispatched work, never resend an unknown attempt. An unrelated connection remains independently usable.
- Render attempt usage and explicit unknown costs as received. Verification applies only to the matching connection revision/profile. Model checks are bounded verification work, not general autonomous business.
- Strict TDD protects rendered workflow and scope/recovery boundaries. Coordinator owns actual-browser/real-profile evidence, shared contracts, project ledger, board and Git.
