# U086: preserve an observed call when checking interrupt settlement

Frozen 2026-11-09 before behavior edits. Exact author combination
`77b457c9e2d3d81f1e55004caf0b8d57bfc2496c` retains PR64/65; integration
`4aa020bf6e528d1d9bc6ab28c5aa8b63cc53fe5c`. #40 comment278;
DSH remains owner. Actor: single codex-home duty implementer; online member
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`.

One 1–2 hour acceptance repair, not a new slice: after the original output
gate establishes text for the exact original model request, both its settled
and reopened states must retain the call as `unknown` or `used`. `released`
cannot establish success for this observed request, even if both snapshots
agree and its reservation has already disappeared. Unknown keeps its
reservation; used may retain null usage when the provider did not report it.

Scope is the interrupt driver's two acceptance assertions. General snapshot
comparison still permits other, genuinely unexecuted steps to be released.
No product accounting/schema/authorization/transaction or timeout changes;
no manufactured tokens, replay, new request, or live-state repair. Existing
AU/Work/attempt/step/command/model identity, current-session checks, complete
cancel GET and snapshot preservation remain in force (D-05/R-05/K-04).

Execute exact original fragments with an observed output before settlement;
keep legitimate unknown/used controls. Verify separately through actual
Chrome/Core HTTP/SQLite/restart with explicit fault injection; never execute
the real driver main. Strict RED before minimal GREEN, npm/Python gates,
exact-head CI and another engineering role's review before integration.
Controlled calls are counted separately from real calls (zero). #22/#39/#40
real exits, histories, owner and WIP remain. Existing dirty files, normal index,
private configs, supervision, schedules and locks are untouched.
