# U-081 independent engineering review

2026-11-08. Implementer: chatGPT-online. Reviewer: codex-home, in a separate
review session, without changing the candidate's product source.

Reviewed [PR #26](https://github.com/illusionaireal/Union/pull/26) at exact head
`6b50769e33b85172289b3badd6faf361a588ec19`, tree
`1030e6f43118b9416fef25d568536fd9bf269435`, based on merged PR #17 at `bbe8068`.
No blocking finding in this limited read-only change. Adoption still requires
every check on the current head to pass.

## Code and boundary findings

- The real core tasks route now mounts WorkPanel alongside the existing
  responsibility workspace. Prepared and legacy routing retain their prior behavior.
- The core instance sets readOnly, hides manual work mutations and guards the
  send function. This does not implement automatic dispatch or request recovery UI.
- Remount and query keys include the current principal, service instance and AU.
  Work protocol, principal and organization mismatches hide records and download
  links. Existing workspace validation checks the trusted session/service/AU
  projection before mounting. No server authorization or schema support changed.
- Result download remains a same-origin endpoint with current server-side
  authorization. An unauthenticated request for the previously readable result
  returns 401.

## Independently executed validation

`npm run check` passes on the exact candidate: 215 frontend tests, 37 management
tests, 9 action tests, types and build. Windows uses the pinned Node 24.19.0 and
the existing project Python environment. No dependencies or lockfiles changed.

The author's `scripts/u081-work-read-browser.cjs` passes six checks in real
Chrome against isolated HTTP/SQLite. The same six checks were downloaded and
verified from Linux CI [run 42464535695](https://github.com/illusionaireal/Union/actions/runs/42464535695),
artifact `13610803664`, with the exact candidate head. The CI step ran and
succeeded; artifact presence alone was not used as evidence.

The additional [review probe](independent-browser-probe.cjs) passes seven checks:
downloaded stored content, principal/AU/protocol mismatch rejection, removal of
previously displayed work after a 403 refresh, download rejection after clearing
the session, and zero work POSTs throughout the browser interaction.

Two initial review-probe runs timed out because an exact-text selector did not
match Card text containing sibling elements. The page already displayed the
correct denial and no work list. Correcting that reviewer selector passed;
this was not a product defect or a product RED/GREEN change.

Full sanitized results are in [independent-verification.json](independent-verification.json).
Run the additional probe after building the console with `UNION_PYTHON` and
`UNION_CHROMIUM_PATH` set to the existing host executables:

```sh
node evidence/U-081/independent-browser-probe.cjs
```

All model activity uses an explicit loopback double. Real model calls: zero.
No NAS business-service switch, real data migration or parent S03 acceptance.
PR #22 drivers remain with DSH; PR #24/#25 still need a different engineering
role's review because codex-home implemented those candidates.

## Shared HTTP fixture follow-up

The final base CI included a failure in Windows job `128680865622`: the shared
four-second HTTP helper timed out during AU creation, before the privacy
assertions. Another same-head Windows job passed. Codex-home took the limited
fixture repair in Kanban #35 comment #55; this repair is authored by the reviewer,
so this document does not claim an independent review of that repair.

The [frozen contract](http-fixture-contract.md) and
[verification](http-fixture-verification.json) preserve the delayed real-loopback
RED and GREEN. The only test-helper change raises its socket wait to 30 seconds;
the original POST is sent once and the original saved receipt is checked.
Product authorization, timeouts, identity/privacy assertions, and CI gates remain
as reviewed. The final complete Windows Python run passes 707 tests, 8 skipped,
in 427.405 seconds; npm check passes. Two earlier local runs ended without a
unittest summary and are not counted as passing runs. Current candidate CI and
the other engineer's review remain the integration conditions.
