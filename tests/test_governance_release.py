"""Installed code compatibility checks the actual adopted AU schema, read-only."""
from pathlib import Path
import sys
from unittest.mock import patch
import zipfile

from scripts import release_package as release
from tests.governance_support import GovernanceCase


class GovernanceReleaseTests(GovernanceCase):
    def install(self, name, schemas):
        payload = {"ai_union/__init__.py": b"# isolated compatibility candidate\n"}
        manifest = {"schema_version": 1, "release_id": name, "git_baseline": "0" * 40,
                    "source_state": "controlled", "core_schemas": {"auth": 2, "catalog": 1},
                    "toolchain": {"bun": "1.4.2"},
                    "files": {key: {"size": len(value), "sha256": release.digest(value)} for key, value in payload.items()}}
        if schemas is not None:
            manifest["core_au_schemas"] = schemas
        path = self.root / (name + ".zip")
        with zipfile.ZipFile(path, "w") as output:
            for key, value in (payload | {"manifest.json": release.encoded(manifest)}).items():
                output.writestr(key, value)
        self.release_config = {"installation_root": self.root / "installation", "console_state": self.root,
                       "python": Path(sys.executable), "bun": self.root / "bun", "console_port": 8766,
                       "modeld_config": self.root / "modeld.json"}
        return release.install(path, self.release_config)

    def test_candidate_cannot_select_or_roll_back_to_code_without_adopted_au_schema_support(self):
        self.prepare(); self.activate()
        au_bytes = self.database().read_bytes()
        self.stop()
        catalog_bytes = (self.root / "console.sqlite3").read_bytes()
        self.install("supported", [1, 2])
        self.install("prepared-only", [1])
        self.install("undeclared", None)
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            release.activate("supported", self.release_config, stopped=True)
            pointer = (self.release_config["installation_root"] / "current.json").read_bytes()
            for candidate in ("prepared-only", "undeclared"):
                with self.subTest(candidate=candidate), self.assertRaises(release.ReleaseError):
                    release.activate(candidate, self.release_config, stopped=True)
                self.assertEqual((self.release_config["installation_root"] / "current.json").read_bytes(), pointer)
        self.assertEqual(self.database().read_bytes(), au_bytes)
        self.assertEqual((self.root / "console.sqlite3").read_bytes(), catalog_bytes)

    def test_a_previously_selected_prepared_only_candidate_cannot_run_after_governance_adoption(self):
        self.prepare()
        self.stop()
        self.install("prepared-only", [1])
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            release.activate("prepared-only", self.release_config, stopped=True)
            self.start()
            self.activate()
            self.stop()
            with patch.object(release.subprocess, "Popen") as spawn:
                with self.assertRaises(release.ReleaseError):
                    release.run("console", self.release_config)
                spawn.assert_not_called()

    def test_malformed_au_schema_declaration_is_rejected_before_install(self):
        for index, value in enumerate(([True], [1, 1], [0], "2")):
            with self.subTest(value=value), self.assertRaises(release.ReleaseError):
                self.install("malformed-" + str(index), value)
