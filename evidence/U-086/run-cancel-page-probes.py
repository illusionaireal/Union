"""Run independent DOM assertions in a disposable exact-source export.

Usage: python run-cancel-page-probes.py <export-directory> <node-executable>
Install the candidate's locked dependencies or link an identical installation
as export-directory/node_modules first. No tracked candidate source is replaced.
Expected result on a3bb2cc: four failures and one passing browsing control.
"""
import subprocess
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
if (source / ".git").exists():
    raise SystemExit("Use a disposable source export, not a developer checkout")
fixture = source / "web/console/src/features/work/page-execution.test.tsx"
prefix = fixture.read_text(encoding="utf-8").split("it('a stale attempt", 1)
if len(prefix) != 2 or "beforeEach" not in prefix[0] or "afterEach" not in prefix[0]:
    raise SystemExit("Candidate fixture changed; review the setup before adapting this probe")
target = fixture.with_name("independent-cancel-page.test.tsx")
with target.open("x", encoding="utf-8") as output:
    output.write(prefix[0])
    output.write(Path(__file__).with_name("cancel-page-probes.tsx").read_text(encoding="utf-8"))
result = subprocess.run(
    [sys.argv[2], str(source / "node_modules/vitest/vitest.mjs"), "run",
     "src/features/work/independent-cancel-page.test.tsx", "--reporter=verbose"],
    cwd=source / "web/console",
)
raise SystemExit(result.returncode)
