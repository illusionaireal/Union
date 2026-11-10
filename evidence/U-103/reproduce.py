"""Inventory immutable Git inputs for the U-103 source audit; never run callers.

This is a search aid, not a security verdict or a test asserting that gaps persist.
Only an explicitly requested, new output file is written. No network is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


QUERIES = {
    "core_import_or_entry": r"from\s+ai_union(?:\.|\s)|import\s+ai_union|ai_union\.(?:application|adapters|engine|console|server)|-m\s+ai_union",
    "storage_or_private_adapter": r"sqlite3|bun:sqlite|node:sqlite|CoreAUStore|GovernanceStore|CreationCatalog|console\.sqlite3|state\.sqlite3",
    "public_http_or_protocol": r"/api/v1/|/api/commands|/api/session|/api/snapshot|create_v1|core\.au\.v1",
    "test_host_import": r"from\s+tests\.|import\s+tests\.",
    "dynamic_import": r"__import__|importlib|import_module",
}
SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sh", ".ps1", ".yml", ".yaml", ".service"}
ANCHORS = (
    "ai_union/server.py", "ai_union/console.py", "ai_union/identity.py",
    "ai_union/identity_schema.py", "ai_union/cli.py", "ai_union/engine.py",
    "ai_union/runner.py", "ai_union/agent_protocol.py",
    "ai_union/model_accounts.py", "ai_union/subscriptions.py",
    "ai_union/gateways.py", "ai_union/company.py", "ai_union/corp.py", "ai_union/model_service.py",
    "ai_union/adapters/au_catalog.py", "ai_union/adapters/core_au_store.py",
    "ai_union/application/creation.py", "ai_union/application/governance.py",
    "ai_union/application/model_access.py", "ai_union/application/work.py",
    "tests/test_core_creation.py", "tests/test_core_isolation.py",
    "tests/test_catalog_integrity.py", "tests/test_identity_upgrade.py",
    "docs/UNION_CHARTER_v1.0.md", "docs/decisions/0005-au-runtime-boundaries.md",
    "specs/053-union-rewrite/s01-contract.md", "pyproject.toml", "package.json",
)


def candidate(path):
    parts = Path(path).parts
    return (Path(path).suffix in SUFFIXES or Path(path).name == "package.json") and not (
        parts[0] in {"ai_union", "tests", "evidence", "docs", "specs"}
        or "vendor" in parts or "node_modules" in parts or "test" in parts
        or "tests" in parts or ".test." in path or ".spec." in path
    )


def inventory(root, revision):
    def git(*args, **kwargs):
        return subprocess.check_output(["git", "-C", str(root), *args], **kwargs)

    commit = git("rev-parse", "--verify", revision + "^{commit}").decode().strip()
    rows = git("ls-tree", "-r", "-z", commit).split(b"\0")
    objects, gitlinks = {}, {}
    for row in filter(None, rows):
        metadata, raw_path = row.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        path = raw_path.decode("utf-8")
        if kind == "commit":
            gitlinks[path] = oid
        elif kind == "blob" and (candidate(path) or path in ANCHORS):
            objects[path] = oid
    paths = sorted(objects)
    raw = git("cat-file", "--batch", input=("\n".join(objects[p] for p in paths) + "\n").encode())
    cursor, inputs, matches = 0, {}, {key: [] for key in QUERIES}
    for path in paths:
        end = raw.index(b"\n", cursor)
        oid, kind, size = raw[cursor:end].decode().split()
        if oid != objects[path] or kind != "blob":
            raise ValueError("Git input mismatch")
        start = end + 1
        body = raw[start:start + int(size)]
        cursor = start + int(size) + 1
        inputs[path] = {"git_blob": oid, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        if candidate(path):
            for key, pattern in QUERIES.items():
                lines = [i for i, line in enumerate(body.decode("utf-8").splitlines(), 1) if re.search(pattern, line)]
                if lines:
                    matches[key].append({"path": path, "lines": lines})
    return {
        "scope": "tracked source candidates and named core/contract/test anchors; no execution or deployed-private-code inspection",
        "commit": commit, "gitlinks_excluded": gitlinks,
        "candidate_files": sum(candidate(path) for path in paths),
        "input_files": len(inputs), "queries": QUERIES,
        "matches": matches, "inputs": inputs,
        "interpretation": "Locations require call-chain review; a match is not a bypass, and no match is not proof of security.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.root, args.revision)
    with args.output.open("x", encoding="utf-8", newline="\n") as target:
        json.dump(result, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print(json.dumps({"commit": result["commit"], "candidate_files": result["candidate_files"],
                      "input_files": result["input_files"],
                      "matching_files": {key: len(value) for key, value in result["matches"].items()}}))


if __name__ == "__main__":
    main()
