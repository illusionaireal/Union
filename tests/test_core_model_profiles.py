"""U-075: each model connection profile declares its own capability scope and evidence.

One profile succeeding must not be presented as通用的能力；不支持的项须明确写出。
"""
import os
import unittest
from unittest.mock import patch

from ai_union.domain import model_profiles
from tests.model_access_support import ModelAccessCase

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ProfileScopeTests(ModelAccessCase):
    def test_read_declares_capabilities_per_profile(self):
        capabilities = self.models()["capabilities"]
        self.assertEqual(sorted(capabilities["profiles"]), sorted(model_profiles.PROFILES))
        scope = capabilities["profile_scope"]
        self.assertEqual(sorted(scope), sorted(capabilities["profiles"]))
        self.assertEqual(sorted(scope["openai_compatible"]["capabilities"]),
                         sorted(model_profiles.CAPABILITIES))
        self.assertEqual(scope["openai_compatible"]["capabilities"]["text_answer"]["status"], "verified_real")
        self.assertEqual(scope["openai_compatible"]["capabilities"]["text_answer"]["evidence"],
                         "evidence/058-s02-model-tools/README.md")
        for capability in ("streaming", "cancel_and_query"):
            claim = scope["openai_compatible"]["capabilities"][capability]
            self.assertEqual(claim["status"], "verified_real")
            self.assertIn("Go deepseek-v4.1-flash", claim["note"])
            self.assertEqual(claim["evidence"], "evidence/U-075/go-deepseek-2026-11-10/README.md")
            self.assertEqual(scope["modeld_grant"]["capabilities"][capability]["status"], "controlled")
            responses = scope["openai_responses"]["capabilities"][capability]
            self.assertEqual(responses["status"], "verified_real")
            self.assertIn("Go GPT-6 Luna", responses["note"])
            self.assertEqual(responses["evidence"], "evidence/U-100/README.md")
        self.assertIn("未确认远端取消", scope["openai_compatible"]["capabilities"]["cancel_and_query"]["note"])
        self.assertEqual(scope["openai_compatible"]["capabilities"]["long_job_new_input"]["status"], "unsupported")
        self.assertEqual(scope["modeld_grant"]["capabilities"]["tool_roundtrip"]["status"], "controlled")

    def test_no_profile_claims_more_than_recorded_evidence(self):
        for name, profile in model_profiles.PROFILES.items():
            self.assertEqual(sorted(profile["capabilities"]), sorted(model_profiles.CAPABILITIES), name)
            self.assertTrue(profile["title"].strip(), name)
            for capability, claim in profile["capabilities"].items():
                self.assertIn(claim["status"], model_profiles.STATUSES, (name, capability))
                self.assertTrue(claim["note"].strip(), (name, capability))
                if claim["status"] == "unsupported":
                    self.assertNotIn("evidence", claim, (name, capability))
                else:
                    path = claim["evidence"]
                    self.assertTrue(os.path.exists(os.path.join(REPO, path)), (name, capability, path))

    def test_registry_decides_which_profiles_new_connections_may_use(self):
        data = {"connection_id": "connection-a", "expected_revision": 0, "name": "Test connection",
                "profile": "modeld_grant", "model": "model-a", "max_output_tokens": 256,
                "grant_ref": "grant-a", "grant_revision": 1}
        remaining = {k: v for k, v in model_profiles.PROFILES.items() if k != "modeld_grant"}
        with patch.object(model_profiles, "PROFILES", remaining):
            before = self.dump()
            status, value, _ = self.model_command("save_connection", data,
                                                  version=self.read()["au"]["version"])
            self.assertEqual(status, 400, value)
            self.assertEqual(value["code"], "invalid_request")
            self.assertEqual(self.dump(), before)
            self.assertNotIn("modeld_grant", self.models()["capabilities"]["profiles"])


if __name__ == "__main__":
    unittest.main()
