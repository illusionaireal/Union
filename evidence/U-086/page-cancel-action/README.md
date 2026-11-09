# U086: page cancellation and original-request recovery

2026-11-09. Base PR62 `e6a8b86879f5712020d0f56cb1714d711754d95c`;
task branch `codex/u086-page-cancel-action`. #40 comment271 was confirmed by
GET200 at revision809. DSH remains owner/progress/WIP; #60/U106 is already
done. Implementer: the single codex-home duty session, online member
`c18f0d21-1d63-4e37-af3e-2dbb78d75995`.

The interrupt driver previously posted cancel_step directly. It could report
success with the actual cancel button removed and could not recover a lost
POST response. It now clicks the original Work's Core cancel control, captures
the page-generated command, refreshes, and clicks that Work's original cancel
query. AU/Work/step/model request/principal/service/version remain bound; no
API fallback or replacement command is issued. Existing complete receipt,
output, snapshot, usage/reservation and restart assertions remain in place.

[Contract](contract.md) was frozen before edits. The exact original-output and
cancel fragments ran in real Chrome against Core HTTP/SQLite with an explicit
fake streaming model. Three original scenarios were RED: no actual clicks,
removed button still accepted, and lost response failed recovery. All three
became GREEN. The first probe launch had a JavaScript syntax error; that log
is retained separately and is not behavioral RED.

The final eight Chrome scenarios pass: normal, missing button, lost response,
no original output, replaced receipt, HTTP403, principal change, service change.
Successful runs make one run_loop and one cancel_step POST, use both actual
controls, and preserve the original receipt after SQLite/server restart.
Missing button/output makes no cancel POST. All keep used=0/reserved=1;
interrupted/unknown does not release the original reservation. Fourteen host
scenarios across RED/initial GREEN/final GREEN use 14 explicit fake model
requests and 11 fake cancellations; real model requests are zero.

31 new Node boundaries and all 216 related Node tests pass. The real-browser
probe is included in existing console-browser CI. Full npm/Python results,
exact source hashes and classified private-log hashes are in
[validation.json](validation.json). Logs, runtime data and credentials stay
host-local. The normal checkout's 20 pre-existing files, vendor and index are
preserved; this task uses an isolated source archive and task ref within the
same non-synchronized checkout, without another worktree or agent.

This is an acceptance-driver repair; product ai_union/web/services bytes,
shared transactions, original call limits and registration remain unchanged.
Current-head CI and another engineering role's review are still required.
The implementation session does not approve itself. #22/#39/#40 real exits,
historical139, complete source/content/usage evidence and remote dispatch
counts remain separate. No real inference, grants, deployment, migration,
sustained business, supervisor/configuration/lock changes occurred.

Final local gates: Python 808 tests / 10 skipped / 0 failures (527.506s); npm check passes with 225 Node, 363 frontend and 37 management tests, typecheck and build. Final management checks also pass.
