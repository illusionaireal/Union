"""U106: real HTTP/SQLite, explicit fake model through the existing automatic loop."""
import hashlib
import sqlite3
from unittest.mock import patch

from tests.model_access_support import ModelAccessCase
from tests import test_core_work as support


class ResultDeliveryTests(ModelAccessCase):
    work_command = support.CoreWorkTests.work_command
    works = support.CoreWorkTests.works
    prepare_materials = support.CoreWorkTests.prepare_materials

    def prepare_candidate(self):
        self.saved()
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                               "enabled": True, "make_default": True})
        self.allow_documents()
        self.prepare_materials()
        self.work_command(self.au_id, "start_work", support.work_data())
        self.work_command(self.au_id, "start_attempt", {"work_id": "work-overview"})
        self.channel = support.FakeTransport([
            ({"content": None, "tool_calls": [{"id": "read-1", "type": "function", "function": {
                "name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]},
             {"input_tokens": 8, "output_tokens": 2}),
            ({"content": "# 概览\n依据 nested/a.md：a 正文\n", "tool_calls": []},
             {"input_tokens": 15, "output_tokens": 5}),
        ])
        self.app.work.transport = self.channel
        status, value, self.loop_request = self.work_command(self.au_id, "run_loop", {"work_id": "work-overview"})
        self.assertEqual((status, value["receipt"]["status"]), (200, "succeeded"), value)
        self.assertEqual(len(self.channel.calls), 2)
        self.assertIn("a 正文", str(self.channel.calls[1]["messages"]))
        self.result = self.works()["works"][0]["results"][0]
        self.data = {"work_id": "work-overview", "result_id": self.result["id"]}

    def download(self, work_id="work-overview"):
        return self.request("/api/v1/work/results?organization_id=" + self.au_id
                            + "&id=" + self.result["id"] + "&work_id=" + work_id)

    def test_disabled_connection_does_not_disable_result_governance_or_recovery(self):
        self.prepare_candidate()
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                               "enabled": False, "make_default": False})
        before = self.dump()
        access = self.works()["access"]
        self.assertFalse(access["can_start"])
        self.assertIs(access.get("can_manage_results"), True)
        self.assertEqual(self.dump(), before, "eligibility read must not write")
        originals = []
        for kind in ("adopt_result", "deliver_work"):
            status, body, request = self.work_command(self.au_id, kind, self.data)
            self.assertEqual((status, body["receipt"]["status"]), (200, "succeeded"), body)
            originals.append((request, body["receipt"]))
        self.stop()
        self.start()
        for request, receipt in originals:
            lookup = self.request("/api/v1/governance/receipts?organization_id=" + self.au_id + "&id=" + request["id"])
            self.assertEqual(lookup[1]["receipt"], receipt)
            self.assertEqual(self.request("/api/v1/work/commands", request)[1]["receipt"], receipt)
        work = self.works()["works"][0]
        self.assertEqual(work["status"], "delivered")
        self.assertEqual(work["budget"]["used"], 2)
        status, download, _ = self.download()
        self.assertEqual(status, 200)
        self.assertEqual(download.get("work_id"), "work-overview")
        self.assertEqual(download["result"]["id"], self.result["id"])
        self.assertEqual(download["result"]["sources"], self.result["sources"])
        self.assertEqual(hashlib.sha256(download["content"].encode()).hexdigest(), self.result["sha256"])
        self.assertEqual(len(self.channel.calls), 2)
        self.assertEqual(self.provider.requests, {})

    def test_adoption_closes_only_the_finished_loop_attempt_with_original_evidence(self):
        self.prepare_candidate()
        original = self.works()["works"][0]["attempts"][0]
        self.assertEqual(original["status"], "running", "RED input is the existing automatic loop behavior")
        status, body, _ = self.work_command(self.au_id, "adopt_result", self.data)
        self.assertEqual((status, body["receipt"]["status"]), (200, "succeeded"))
        item = self.works()["works"][0]
        self.assertEqual(item["attempts"][0]["status"], "closed")
        self.assertEqual(item["attempts"][0]["outcome"], "stopped")
        self.assertIn(self.loop_request["id"], item["attempts"][0]["reason"])
        self.assertNotEqual(item["status"], "delivered")

    def test_adoption_does_not_close_when_the_final_loop_receipt_is_missing(self):
        save = self.app.work.store_receipt
        def without_parent(directory, intent, request, principal, receipt):
            if request["kind"] == "run_loop":
                return receipt  # controlled lost parent commit, child facts remain
            return save(directory, intent, request, principal, receipt)
        with patch.object(self.app.work, "store_receipt", side_effect=without_parent):
            self.prepare_candidate()
        self.work_command(self.au_id, "adopt_result", self.data)
        self.assertEqual(self.works()["works"][0]["attempts"][0]["status"], "running")
        self.assertEqual(self.work_command(self.au_id, "deliver_work", self.data)[1]["receipt"]["status"], "rejected")

    def test_adoption_never_closes_a_new_attempt(self):
        self.prepare_candidate()
        first = self.works()["works"][0]["attempts"][0]["id"]
        self.work_command(self.au_id, "finish_attempt", {"work_id": "work-overview", "attempt_id": first,
                          "outcome": "stopped", "reason": "controlled lifecycle precondition"})
        self.work_command(self.au_id, "start_attempt", {"work_id": "work-overview"})
        self.work_command(self.au_id, "adopt_result", self.data)
        self.assertEqual(self.works()["works"][0]["attempts"][-1]["status"], "running")
        self.assertEqual(self.work_command(self.au_id, "deliver_work", self.data)[1]["receipt"]["status"], "rejected")

    def test_adoption_preserves_an_unresolved_call_and_reservation(self):
        self.prepare_candidate()
        with patch.object(self.channel, "chat", side_effect=TimeoutError("controlled unknown call")):
            self.work_command(self.au_id, "run_step", {"work_id": "work-overview"})
        self.work_command(self.au_id, "adopt_result", self.data)
        item = self.works()["works"][0]
        self.assertEqual(item["attempts"][0]["status"], "running")
        self.assertEqual(item["steps"][-1]["status"], "unknown")
        self.assertEqual(item["budget"]["reserved"], 1)

    def test_download_rejects_a_different_work_even_with_a_valid_result_id(self):
        self.prepare_candidate()
        self.assertEqual(self.download("another-work")[0], 400)

    def test_expired_governance_preserves_read_and_original_lookup_but_denies_new_adoption(self):
        self.prepare_candidate()
        deadline = self.read()["au"]["governance"]["valid_until"]
        with patch("time.time", return_value=deadline + 1):
            self.assertFalse(self.works()["access"]["can_manage_results"])
            status, body, _ = self.work_command(self.au_id, "adopt_result", self.data)
            self.assertEqual((status, body["receipt"]["status"]), (200, "rejected"))
            self.assertEqual(self.download()[0], 200)
            self.assertEqual(self.request("/api/v1/governance/receipts?organization_id=" + self.au_id
                                         + "&id=" + self.loop_request["id"])[0], 200)
        self.assertEqual(self.works()["works"][0]["results"][0]["status"], "candidate")

    def test_stale_version_and_foreign_principal_cannot_adopt(self):
        self.prepare_candidate()
        version = self.works()["version"]
        status, body, _ = self.work_command(self.au_id, "adopt_result", self.data, version=version - 1)
        self.assertEqual((status, body["receipt"]["status"]), (200, "rejected"))
        token, _ = self.participant("result-outsider")
        self.assertEqual(self.work_command(self.au_id, "adopt_result", self.data, version=version, token=token)[0], 403)
        self.assertEqual(self.request("/api/v1/work?organization_id=" + self.au_id, token=token)[0], 403)
        self.assertEqual(self.works()["works"][0]["results"][0]["status"], "candidate")
        self.assertEqual(len(self.channel.calls), 2)

    def test_failed_commit_preserves_candidate_and_does_not_publish_receipt(self):
        self.prepare_candidate()
        before = self.dump()
        with patch.object(self.app.work.store, "save", side_effect=sqlite3.OperationalError("controlled commit failure")):
            status, _, original = self.work_command(self.au_id, "adopt_result", self.data)
        self.assertGreaterEqual(status, 400)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.request("/api/v1/governance/receipts?organization_id=" + self.au_id + "&id=" + original["id"])[0], 403)
        self.assertEqual(len(self.channel.calls), 2)
