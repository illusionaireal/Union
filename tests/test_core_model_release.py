"""Schema 3 must be declared by a built candidate and enforced when selected."""
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import release_package as release
from tests.model_access_support import ModelAccessCase
from tests import test_governance_release as governance_release

REPOSITORY = Path(__file__).resolve().parents[1]


class CoreModelReleaseTests(ModelAccessCase):
    install = governance_release.GovernanceReleaseTests.install

    def test_prior_candidate_stops_at_schema_three_without_erasing_latest_state(self):
        self.install("governance-only", [1, 2])
        self.install("models-supported", [1, 2, 3])
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            release.activate("governance-only", self.release_config, stopped=True)
            self.saved()
            before = self.dump()
            pointer = (self.release_config["installation_root"] / "current.json").read_bytes()
            with self.assertRaises(release.ReleaseError):
                release.activate("governance-only", self.release_config, stopped=True)
            with patch.object(release.subprocess, "Popen") as spawn:
                with self.assertRaises(release.ReleaseError):
                    release.run("console", self.release_config)
                spawn.assert_not_called()
            self.assertEqual((self.release_config["installation_root"] / "current.json").read_bytes(), pointer)
            self.assertEqual(self.dump(), before)
            release.activate("models-supported", self.release_config, stopped=True)
            self.assertEqual(self.dump(), before)

    @unittest.skipUnless((REPOSITORY / "services/modeld/dist/main.js").is_file()
                         and (REPOSITORY / "web/console/dist/index.html").is_file(), "Build both products before checking the package declaration")
    def test_built_candidate_declares_its_actual_model_schema(self):
        self.saved()
        from ai_union.domain import model_profiles
        # A packer may run outside its --root; its loaded modules must not declare
        # capabilities that differ from the exact source being packaged.
        with patch.object(model_profiles, "PROFILES", {"modeld_grant": {}}):
            manifest = release.pack(REPOSITORY, self.root / "model-schema.zip", "model-schema-test")
        self.assertIn(3, manifest["core_au_schemas"])
        self.assertEqual(manifest["modeld_schemas"], [0, 1])
        self.assertIn("openai_responses", manifest["core_model_profiles"])
        release.check_core_schemas(manifest, {"console_state": self.root})
