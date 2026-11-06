"""Supported code selection must not reinterpret persisted Responses accounts."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import release_package as release


class ModeldReleaseSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="union-modeld-release-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        private = self.root / "private"
        private.mkdir()
        self.config_file = private / "modeld.json"
        self.config_file.write_text(json.dumps({"state_directory": "state"}), encoding="utf-8")
        (private / "state").mkdir()
        self.database = private / "state" / "modeld.sqlite3"
        with closing(sqlite3.connect(self.database)) as cx:
            cx.execute("CREATE TABLE original_requests(id TEXT PRIMARY KEY, result TEXT)")
            cx.execute("INSERT INTO original_requests VALUES('original', 'unknown')")
            cx.commit()
        self.config = {"installation_root": self.root / "installation", "console_state": self.root / "core",
                       "modeld_config": self.config_file}

    def manifest(self, name, schemas=None):
        manifest = {"schema_version": 1, "release_id": name,
                    "files": {"ai_union/__init__.py": {"size": 0, "sha256": release.digest(b"")}}}
        if schemas is not None:
            manifest["modeld_schemas"] = schemas
        return manifest

    def install(self, name, schemas=None):
        manifest = self.manifest(name, schemas)
        package = self.root / (name + ".zip")
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("manifest.json", release.encoded(manifest))
            archive.writestr("ai_union/__init__.py", b"")
        release.install(package, self.config)

    def test_explicit_protocol_adoption_blocks_old_code_selection_and_run(self):
        self.install("old-chat")
        self.install("responses", [0, 1])
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            release.activate("old-chat", self.config, stopped=True)
            with closing(sqlite3.connect(self.database)) as cx:
                cx.execute("PRAGMA user_version=1")
            before = self.database.read_bytes()
            pointer = (self.config["installation_root"] / "current.json").read_bytes()
            with self.assertRaisesRegex(release.ReleaseError, "modeld"):
                release.activate("old-chat", self.config, stopped=True)
            with patch.object(release.subprocess, "Popen") as spawn:
                with self.assertRaisesRegex(release.ReleaseError, "modeld"):
                    release.run("modeld", self.config)
                spawn.assert_not_called()
            self.assertEqual((self.config["installation_root"] / "current.json").read_bytes(), pointer)
            self.assertEqual(self.database.read_bytes(), before)
            release.activate("responses", self.config, stopped=True)
            self.assertEqual(self.database.read_bytes(), before)

    def test_malformed_private_schema_declarations_are_rejected(self):
        for schemas in ([True], [0, 0], [-1], "1", []):
            with self.subTest(schemas=schemas), self.assertRaises(release.ReleaseError):
                release.validate_manifest(self.manifest("invalid", schemas))

    def test_unknown_or_corrupt_private_database_cannot_be_selected(self):
        with closing(sqlite3.connect(self.database)) as cx:
            cx.execute("PRAGMA user_version=8")
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(self.manifest("known", [0, 1]), self.config)
        self.database.write_bytes(b"invalid SQLite")
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(self.manifest("known", [0, 1]), self.config)
