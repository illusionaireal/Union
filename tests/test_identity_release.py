"""Code switching must not let an incompatible candidate write new identities."""
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
import zipfile
import sqlite3
from contextlib import closing

from ai_union.console import Console
from scripts import release_package as release


class IdentityReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {"installation_root": self.root / "code", "console_state": self.root / "state",
                       "python": Path(sys.executable), "bun": self.root / "bun", "console_port": 8766,
                       "modeld_config": self.root / "private/modeld.json"}

    def install(self, release_id, schemas=None):
        payload = {"ai_union/__init__.py": b"# controlled code candidate\n"}
        manifest = {"schema_version": 1, "release_id": release_id, "git_baseline": "0" * 40,
                    "source_state": "controlled", "toolchain": {"bun": "1.4.2"},
                    "files": {p: {"size": len(b), "sha256": release.digest(b)} for p, b in payload.items()}}
        if schemas is not None:
            manifest["core_schemas"] = schemas
        archive = self.root / (release_id + ".zip")
        with zipfile.ZipFile(archive, "w") as output:
            for path, data in (payload | {"manifest.json": release.encoded(manifest)}).items():
                output.writestr(path, data)
        release.install(archive, self.config)

    def create_current_catalog(self):
        app = Console(self.config["console_state"])
        try:
            app.identity.setup(None, "owner", "correct-horse-password", True)
        finally:
            app.close()
        return (self.config["console_state"] / "console.sqlite3").read_bytes()

    def test_incompatible_activation_and_rollback_preserve_pointer_and_latest_identity(self):
        self.install("old")
        self.install("current", {"auth": 1, "catalog": 1})
        self.install("future", {"auth": 2, "catalog": 2})
        current_bytes = self.create_current_catalog()
        # Only external dependency checks are replaced; real manifests and SQLite
        # compatibility must still protect the code-switching boundary.
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            for candidate in ("old", "future"):
                with self.subTest(candidate=candidate):
                    release.activate("current", self.config, stopped=True)
                    pointer = (self.config["installation_root"] / "current.json").read_bytes()
                    with self.assertRaises(release.ReleaseError):
                        release.activate(candidate, self.config, stopped=True)
                    self.assertEqual((self.config["installation_root"] / "current.json").read_bytes(), pointer)
                    self.assertEqual((self.config["console_state"] / "console.sqlite3").read_bytes(), current_bytes)

    def test_run_refuses_a_previously_selected_old_binary_after_schema_upgrade(self):
        self.install("old")
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            release.activate("old", self.config, stopped=True)
            current_bytes = self.create_current_catalog()
            with patch.object(release.subprocess, "Popen") as spawn:
                with self.assertRaises(release.ReleaseError):
                    release.run("console", self.config)
                spawn.assert_not_called()
        self.assertEqual((self.config["console_state"] / "console.sqlite3").read_bytes(), current_bytes)

    def test_incomplete_current_schema_rejects_before_switching_code_pointer(self):
        self.install("current", {"auth": 1, "catalog": 1})
        self.install("candidate", {"auth": 1, "catalog": 1})
        self.create_current_catalog()
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            release.activate("current", self.config, stopped=True)
            pointer = (self.config["installation_root"] / "current.json").read_bytes()
            database = self.config["console_state"] / "console.sqlite3"
            with closing(sqlite3.connect(database)) as cx, cx:
                cx.execute('ALTER TABLE core_schema RENAME COLUMN upgrade_receipt TO lost_receipt')
            before = database.read_bytes()
            with self.assertRaises(release.ReleaseError):
                release.activate("candidate", self.config, stopped=True)
            self.assertEqual((self.config["installation_root"] / "current.json").read_bytes(), pointer)
            self.assertEqual(database.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
