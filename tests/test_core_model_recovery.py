"""S02 recovery follows original intents and preserves factual resource use."""
from contextlib import closing
import json
import sqlite3
from unittest.mock import patch

from tests.model_access_support import ModelAccessCase


class CoreModelRecoveryTests(ModelAccessCase):
    def ready(self, calls=6):
        self.saved()
        self.allow_documents()
        self.resource_grant(calls)

    def stop_before_second_reservation(self):
        runner = self.app.models.check_runner
        reserve = runner.reserve

        def interrupted(state, charter, cx, principals, check_id):
            if state["model_access"]["checks"][check_id]["stage"] == 1:
                raise OSError("controlled interruption after the tool commit")
            return reserve(state, charter, cx, principals, check_id)

        with patch.object(runner, "reserve", side_effect=interrupted):
            receipt, _ = self.start_check()
            check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "unknown", check)
        self.assertEqual(check["stage"], 1)
        self.assertEqual(len(self.provider.requests), 1)
        return check

    def test_unsent_prepared_attempt_can_resume_with_its_original_id(self):
        self.ready()
        with patch.object(self.app.models.check_runner, "dispatch", side_effect=OSError("before dispatch intent")):
            receipt, _ = self.start_check()
            original = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(original["status"], "unknown", original)
        self.assertEqual(self.provider.requests, {})
        self.assertEqual(original["attempts"][0]["state"], "prepared")
        self.stop(); self.start()
        self.model_success("reconcile_model_check", {"check_id": original["id"]})
        resumed = self.wait_for("checks", original["id"])
        self.assertEqual(resumed["status"], "succeeded", resumed)
        self.assertEqual(resumed["attempt_ids"][0], original["attempt_ids"][0])
        self.assertEqual(len(self.provider.requests), 2)

    def test_cancel_releases_only_the_never_dispatched_reservation(self):
        self.ready(calls=2)
        with patch.object(self.app.models.check_runner, "dispatch", side_effect=OSError("before dispatch intent")):
            receipt, _ = self.start_check()
            check = self.wait_for("checks", receipt["check_id"])
        self.model_success("cancel_model_check", {"check_id": check["id"], "reason": "Withdraw this unsent check"})
        self.wait_for("checks", check["id"])
        self.app.join_jobs()
        self.assertEqual(self.provider.requests, {})
        self.assertEqual(self.models()["resources"]["reserved_calls"], 0)
        next_receipt, _ = self.start_check()
        self.assertEqual(self.wait_for("checks", next_receipt["check_id"])["status"], "succeeded")

    def test_terminal_provider_failure_releases_only_the_unused_second_call(self):
        self.ready(calls=3)
        self.provider.result_state = "failed"
        receipt, _ = self.start_check()
        failed = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(failed["status"], "failed", failed)
        self.assertEqual(failed["attempts"][0]["usage"]["input_tokens"], 25)
        self.assertEqual(self.models()["resources"]["reserved_calls"], 1)
        self.provider.result_state = "completed"
        next_receipt, _ = self.start_check()
        self.assertEqual(self.wait_for("checks", next_receipt["check_id"])["status"], "succeeded")
        self.assertEqual(len(self.provider.requests), 3)

    def test_restart_after_tool_commit_continues_only_the_second_inference(self):
        self.ready()
        original = self.stop_before_second_reservation()
        self.stop(); self.start()
        self.model_success("reconcile_model_check", {"check_id": original["id"]})
        resumed = self.wait_for("checks", original["id"])
        self.assertEqual(resumed["status"], "succeeded", resumed)
        self.assertEqual(resumed["attempt_ids"][0], original["attempt_ids"][0])
        self.assertEqual(len(self.provider.requests), 2)
        with closing(sqlite3.connect(self.database())) as cx:
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM model_tool_receipts").fetchone()[0], 1)

    def test_graceful_host_stop_after_tool_commit_keeps_the_check_recoverable(self):
        self.ready()
        runner = self.app.models.check_runner
        accept = runner.accept

        def accepted_then_stop(state, charter, cx, principals, check_id, stage, remote):
            result = accept(state, charter, cx, principals, check_id, stage, remote)
            if stage == 0:
                self.app.models.stopping = True
            return result

        with patch.object(runner, "accept", side_effect=accepted_then_stop):
            receipt, _ = self.start_check()
            check = self.wait_for("checks", receipt["check_id"])
        self.assertEqual(check["status"], "unknown", check)
        self.assertEqual(len(self.provider.requests), 1)
        self.stop(); self.start()
        self.model_success("reconcile_model_check", {"check_id": check["id"]})
        self.assertEqual(self.wait_for("checks", check["id"])["status"], "succeeded")
        self.assertEqual(len(self.provider.requests), 2)

    def test_modified_tool_receipt_is_rejected_before_second_dispatch(self):
        self.ready()
        original = self.stop_before_second_reservation()
        with closing(sqlite3.connect(self.database())) as cx, cx:
            raw = cx.execute("SELECT result FROM model_tool_receipts WHERE check_id=?", (original["id"],)).fetchone()[0]
            changed = json.loads(raw)
            changed["content"] = "Unselected replacement material"
            cx.execute("UPDATE model_tool_receipts SET result=? WHERE check_id=?", (json.dumps(changed), original["id"]))
        self.model_success("reconcile_model_check", {"check_id": original["id"]})
        refused = self.wait_for("checks", original["id"])
        self.assertEqual(refused["status"], "failed", refused)
        self.assertEqual(len(self.provider.requests), 1)
        self.assertIsNone(refused["output"])

    def test_save_committed_remotely_survives_host_loss_before_local_adoption(self):
        data = {"connection_id": "api-a", "expected_revision": 0, "name": "Private API", "profile": "openai_compatible",
                "model": "model-a", "max_output_tokens": 256, "base_url": "https://model.example.invalid/v1", "api_key": "controlled-api-key"}
        with patch.object(self.app.models, "spawn"):
            receipt, _ = self.model_success("save_connection", data)
        self.provider.call("POST", "/v1/api-connections", {"id": receipt["operation_id"], "au_id": self.au_id,
            "principal_id": self.principal, "name": data["name"], "base_url": data["base_url"], "api_key": data["api_key"], "model_id": data["model"]})
        self.stop(); self.start()
        operation = self.models()["operations"][0]
        self.assertEqual(operation["status"], "unknown", operation)
        self.model_success("reconcile_connection", {"operation_id": receipt["operation_id"]})
        self.assertEqual(self.wait_operation(receipt["operation_id"])["status"], "succeeded")
        self.assertEqual(len(self.provider.posts), 1)
        self.assertEqual(self.models()["connections"][0]["revision"], 1)


if __name__ == "__main__":
    import unittest
    unittest.main()
