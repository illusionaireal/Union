"""Disposable real Core/SQLite; no modeld configuration, grant or inference."""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.exit22b_host import PageHost

for key in ("UNION_MODELD_CONFIG", "UNION_REAL_ACCOUNT", "UNION_REAL_MODEL"):
    os.environ.pop(key, None)
with tempfile.TemporaryDirectory(prefix="union-single-setup-") as directory:
    host = PageHost(Path(directory))
    try:
        print(json.dumps(host.state()), flush=True)
        sys.stdin.readline()
    finally:
        host.stop()
