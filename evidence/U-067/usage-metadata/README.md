# Acceptance usage metadata correction

2026-11-08. Foreground coordinator continues the authorized #22 acceptance-driver
intervention; DSH retains the parent responsibility and real acceptance. The
[contract](../../../specs/053-union-rewrite/s03-acceptance-intervention-contract.md)
was frozen before the failing tests and minimal driver change.

`ModeldWorkTransport.chat` returns the complete provider usage object. Work steps
persist only `input_tokens` and `output_tokens`. Comparing the entire provider
object with a step rejected otherwise valid evidence whenever metadata was present.
The driver now compares the two already validated token counts for each original
request, then their aggregate. Full provider evidence remains intact; cached tokens
are not added a second time. The two-call and 1024-output bounds are unchanged.

The unmodified driver produced two real assertion failures across three checks:
a complete evidence object with provider metadata and the actual local HTTP /
SQLite / document / candidate-download path both failed. The genuine per-step
token mismatch counterexample was already correctly rejected. After the one-line
comparison correction, all **20** intervention and acceptance-guard tests pass.
See [RED](red.txt), [GREEN](green.txt) and [verification](verification.json).

The HTTP test uses an explicitly substituted model and sends no real provider
requests. This engineering correction does not certify any author's previous
real run or complete #22. Full-suite/npm and exact-head CI remain merge gates;
their final results are recorded on PR33 without rewriting the tested source.
