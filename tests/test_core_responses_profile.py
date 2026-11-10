"""S09 Responses connection flow; HTTP/AU persistence with an explicit modeld double."""
import copy
from unittest.mock import patch

from scripts import release_package as release
from tests.model_access_support import ModelAccessCase
from tests.test_governance_release import GovernanceReleaseTests


class ResponsesProfileTests(ModelAccessCase):
    install = GovernanceReleaseTests.install

    def setUp(self):
        super().setUp()
        original = self.provider.call

        def call(method, path, body=None, **kwargs):
            try:
                result = original(method, path, body, **kwargs)
            finally:
                if method == "POST" and path == "/v1/api-connections" and body.get("wire_api") == "responses":
                    self.provider.registrations[body["id"]].update(profile="openai_responses", wire_api="responses")
            if method == "POST" and path == "/v1/api-connections":
                return copy.deepcopy(self.provider.registrations[body["id"]])
            return result

        self.provider.call = call

    def test_save_binds_responses_without_inference_and_reopens_secret_free(self):
        receipt, request = self.saved(profile="openai_responses")
        self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "succeeded")
        connection = self.models()["connections"][0]
        self.assertEqual(connection["profile"], "openai_responses")
        self.assertFalse(connection["is_default"])
        self.assertEqual(self.provider.posts[0][1]["wire_api"], "responses")
        self.assertNotIn(request["data"]["api_key"], self.dump())
        self.assertEqual(self.provider.requests, {})
        self.stop(); self.start()
        self.assertEqual(self.models()["connections"][0], connection)
        self.assertEqual(self.request("/api/v1/models/commands", request)[1]["receipt"], receipt)
        self.assertEqual(len(self.provider.posts), 1)

    def test_lost_registration_looks_up_original_protocol_without_reposting_key(self):
        self.provider.lost_save = True
        receipt, _ = self.saved(profile="openai_responses")
        self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "unknown")
        self.model_success("reconcile_connection", {"operation_id": receipt["operation_id"]})
        self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "succeeded")
        self.assertEqual(self.models()["connections"][0]["profile"], "openai_responses")
        self.assertEqual(len(self.provider.posts), 1)

    def test_wrong_profile_or_wire_receipt_is_not_adopted(self):
        for field, wrong in (("profile", "openai_compatible"), ("wire_api", "chat_completions")):
            with self.subTest(field=field):
                self.provider.lost_save = True
                receipt, _ = self.saved(profile="openai_responses")
                self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "unknown")
                self.provider.registrations[receipt["operation_id"]][field] = wrong
                self.model_success("reconcile_connection", {"operation_id": receipt["operation_id"]})
                self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "rejected")
                self.assertEqual(self.models()["connections"], [])

    def test_bounded_tool_roundtrip_retains_native_context_usage_and_original_result(self):
        self.saved(profile="openai_responses")
        self.allow_documents(); self.resource_grant()
        receipt, _ = self.start_check()
        check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "succeeded", check)
        self.assertEqual(len(self.provider.requests), 2)
        second = list(self.provider.requests.values())[1]
        self.assertIn("_native", second["messages"][-2])
        self.assertEqual([a["usage"]["input_tokens"] for a in check["attempts"]], [25, 25])
        self.assertTrue(all(a["usage"]["cost_minor"] is None for a in check["attempts"]))
        self.assertIn("明确选择的真实本地资料", check["output"])
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                              "enabled": True, "make_default": True})
        self.stop(); self.start()
        self.assertEqual(self.models()["checks"][0]["output"], check["output"])
        self.assertTrue(self.models()["connections"][0]["is_default"])
        self.assertEqual(len(self.provider.requests), 2)

    def test_scope_uses_its_own_selected_responses_real_evidence(self):
        claims = self.models()["capabilities"]["profile_scope"]["openai_responses"]["capabilities"]
        for capability in ("text_answer", "tool_roundtrip", "usage_reporting"):
            self.assertEqual(claims[capability]["status"], "verified_real")
            self.assertEqual(claims[capability]["evidence"], "evidence/U-099/README.md")
            self.assertIn("Go GPT-6 Luna", claims[capability]["note"])
        for capability in ("streaming", "cancel_and_query"):
            self.assertEqual(claims[capability]["status"], "verified_real")
            self.assertEqual(claims[capability]["evidence"], "evidence/U-100/README.md")
            self.assertIn("Go GPT-6 Luna", claims[capability]["note"])
        self.assertIn("未确认提供方已取消", claims["cancel_and_query"]["note"])
        self.assertEqual(claims["long_job_new_input"]["status"], "unsupported")

    def test_legacy_chat_registration_retains_its_original_request_shape(self):
        receipt, _ = self.saved(profile="openai_compatible")
        self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "succeeded")
        self.assertNotIn("wire_api", self.provider.posts[0][1])
        self.assertEqual(self.models()["connections"][0]["profile"], "openai_compatible")

    def test_old_candidate_refuses_new_profile_before_switch_or_restart(self):
        self.install("old-model-profiles", [1, 2, 3])
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            release.activate("old-model-profiles", self.release_config, stopped=True)
            pointer = (self.release_config["installation_root"] / "current.json").read_bytes()
            # Unknown saving intent also needs new code; there need not be an adopted connection yet.
            self.provider.lost_save = True
            receipt, _ = self.saved(profile="openai_responses")
            self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "unknown")
            before = self.dump()
            with self.assertRaises(release.ReleaseError):
                release.activate("old-model-profiles", self.release_config, stopped=True)
            with patch.object(release.subprocess, "Popen") as spawn:
                with self.assertRaises(release.ReleaseError):
                    release.run("console", self.release_config)
                spawn.assert_not_called()
            self.assertEqual((self.release_config["installation_root"] / "current.json").read_bytes(), pointer)
            self.assertEqual(self.dump(), before)
            supported = {"core_au_schemas": [1, 2, 3],
                         "core_model_profiles": ["modeld_grant", "openai_compatible", "openai_responses"]}
            release.check_au_schemas(self.root / "console.sqlite3", supported, self.root)
