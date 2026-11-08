"""Offline counterexamples for the real-acceptance drivers; no provider calls."""
import copy
import hashlib
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tests import test_core_work_real as bounded
from tests import test_core_work_real_interrupt as interrupted


def complete_evidence():
    text = "synthetic verification public-unique-code"
    digest = hashlib.sha256(text.encode()).hexdigest()
    tool = {"role": "tool", "tool_call_id": "read-1", "content": json.dumps({
        "path": "brief.md", "content": text, "sha256": digest, "bytes": len(text.encode())})}
    assistant = {"role": "assistant", "tool_calls": [{"id": "read-1", "type": "function",
        "function": {"name": "read_document", "arguments": '{"path":"brief.md"}'}}]}
    result = {"id": "result-1", "status": "candidate", "sha256": digest,
              "bytes": len(text.encode()), "sources": ["work-real#1"]}
    calls = [{"run_id": "request-1", "messages": [], "usage": {"input_tokens": 10, "output_tokens": 5}},
             {"run_id": "request-2", "messages": [assistant, tool],
              "usage": {"input_tokens": 20, "output_tokens": 7}}]
    work = {"id": "work-real", "budget": {"max_calls": 2, "used": 2, "reserved": 0},
        "usage": {"input_tokens": 30, "output_tokens": 12}, "cost_status": "unknown",
        "tool_calls": [{"tool": "read_document", "sha256": digest, "bytes": len(text.encode()),
                        "step_ref": "work-real#1", "arguments": {"path": "brief.md"}}],
        "steps": [{"status": "used", "model_request_id": c["run_id"], "usage": c["usage"]} for c in calls],
        "results": [result], "_acceptance": {"calls": calls, "document": text, "nonce": "public-unique-code",
            "organization_id": "au-1", "downloads": [{"organization_id": "au-1", "work_id": "work-real",
                                                        "result": result, "content": text}]}}
    receipt = {"status": "succeeded", "turns": 2, "result": True}
    return work, receipt


class Client:
    def __init__(self, remote=None, cancel=None, provider="opencode-go"):
        self.remote = remote or {"id": "target", "au_id": "au-1", "state": "streaming"}
        self.cancel = cancel or {**self.remote, "cancel_requested": True}
        self.provider = provider
        self.posts = []

    def call(self, method, path, body=None, **kwargs):
        if path == "/v1/accounts":
            return {"accounts": [{"id": "chosen", "provider": self.provider}]}
        if method == "POST":
            self.posts.append((path, kwargs))
            if path != "/v1/grants": self.remote = self.cancel
            return {"id": "grant", "revision": 1} if path == "/v1/grants" else self.cancel
        return self.remote

    def events(self, request_id, au_id, after):
        return {"events": [{"request_id": request_id, "seq": 1, "type": "text_delta"}]}


class AcceptanceInterventionTests(unittest.TestCase):
    def test_complete_linked_exchange_is_accepted(self):
        work, receipt = complete_evidence()
        self.assertEqual(bounded.acceptance_problems(work, receipt, 1024), [])

    def test_one_turn_digest_candidate_is_not_a_completed_exchange(self):
        work, receipt = complete_evidence()
        work.pop("_acceptance")
        work["budget"]["used"] = receipt["turns"] = 1
        self.assertTrue(bounded.acceptance_problems(work, receipt, 1024))

    def test_missing_or_forged_context_download_and_source_are_rejected(self):
        for fault in ("no_context", "wrong_tool_id", "wrong_body", "wrong_download", "wrong_scope", "wrong_source"):
            with self.subTest(fault=fault):
                work, receipt = complete_evidence()
                evidence = work["_acceptance"]
                if fault == "no_context": evidence["calls"][1]["messages"] = []
                if fault == "wrong_tool_id": evidence["calls"][1]["messages"][1]["tool_call_id"] = "other"
                if fault == "wrong_body": evidence["document"] = "different document"
                if fault == "wrong_download": evidence["downloads"][0]["content"] = "changed"
                if fault == "wrong_scope": evidence["downloads"][0]["organization_id"] = "another-au"
                if fault == "wrong_source": work["results"][0]["sources"] = []
                self.assertTrue(bounded.acceptance_problems(work, receipt, 1024), fault)

    def test_per_call_limit_and_original_request_ids_are_checked(self):
        for fault in ("over_limit", "duplicate_id", "wrong_step", "wrong_usage"):
            with self.subTest(fault=fault):
                work, receipt = complete_evidence()
                if fault == "over_limit": work["_acceptance"]["calls"][0]["usage"]["output_tokens"] = 1025
                if fault == "duplicate_id": work["_acceptance"]["calls"][1]["run_id"] = "request-1"
                if fault == "wrong_step": work["steps"][0]["model_request_id"] = "other"
                if fault == "wrong_usage": work["usage"]["output_tokens"] = 13
                self.assertTrue(bounded.acceptance_problems(work, receipt, 1024), fault)

    def test_explicit_wrong_provider_never_gets_a_grant(self):
        client = Client(provider="unrelated")
        with patch.dict(os.environ, {"UNION_REAL_ACCOUNT": "chosen"}, clear=True), \
                patch.object(bounded, "ModelServiceClient", return_value=client):
            with self.assertRaises((AssertionError, unittest.SkipTest)):
                bounded.RealChannelCase().grant("au-1")
        self.assertEqual(client.posts, [])

    def test_request_discovery_excludes_other_work_attempt_and_command(self):
        case = interrupted.RealInterruptTests()
        case.target_command = {"organization_id": "au-1", "id": "command-1", "data": {"work_id": "work-real"}}
        case.target_attempt = "attempt-1"
        own = {"model_request_id": "target", "step_ref": "work-real#s2", "attempt_id": "attempt-1", "command_id": "command-1"}
        other = {**own, "model_request_id": "other", "command_id": "previous"}
        card = {"organization_id": "au-1", "works": [{"id": "other-work", "steps": [own]},
            {"id": "work-real", "steps": [other, {**own, "attempt_id": "old"}, own]}]}
        with patch.object(case, "request", return_value=(200, card, {})):
            self.assertEqual(case.wait_for_request_id("au-1", deadline=0.1), ("target", "work-real#s2"))

    def test_mismatched_or_completed_lookup_is_not_cancelled(self):
        for remote in ({"id": "other", "au_id": "other", "state": "streaming"},
                       {"id": "target", "au_id": "au-1", "state": "completed"}):
            case, client, observed = interrupted.RealInterruptTests(), Client(remote), {}
            with patch.object(case, "wait_for_request_id", return_value=("target", "work-real#s1")):
                case.cancel_when_dispatched(client, "au-1", observed)
            self.assertEqual(client.posts, [])
            self.assertFalse(observed.get("cancelled"))

    def test_cancel_response_must_confirm_original_request_and_remain_separate_from_remote_cancellation(self):
        case, observed = interrupted.RealInterruptTests(), {}
        client = Client(cancel={"id": "other", "au_id": "other", "state": "interrupted", "cancel_requested": True})
        with patch.object(case, "wait_for_request_id", return_value=("target", "work-real#s1")):
            case.cancel_when_dispatched(client, "au-1", observed)
        self.assertFalse(observed.get("cancelled"))
        self.assertFalse(observed.get("cancel_requested"))

    def test_scoped_stream_and_acknowledged_interruption_are_distinct_from_remote_cancellation(self):
        case, observed = interrupted.RealInterruptTests(), {}
        client = Client(cancel={"id": "target", "au_id": "au-1", "state": "interrupted", "cancel_requested": True})
        with patch.object(case, "wait_for_request_id", return_value=("target", "work-real#s1")):
            case.cancel_when_dispatched(client, "au-1", observed)
        self.assertTrue(observed["provider_output_observed"])
        self.assertTrue(observed["cancel_requested"])
        self.assertTrue(observed["interrupted"])
        self.assertFalse(observed["remote_cancellation_confirmed"])
        self.assertEqual(len(client.posts), 1)
        self.assertFalse(client.posts[0][1].get("admin", False))

    def test_failed_lookup_or_no_provider_output_cannot_pass_as_interruption(self):
        for failure in (True, False):
            case, observed, client = interrupted.RealInterruptTests(), {}, Client()
            with patch.object(case, "wait_for_request_id", return_value=("target", "work-real#s1")), \
                    patch.object(interrupted.time, "monotonic", side_effect=[0, 0, 26]), \
                    patch.object(client, "events", return_value={"events": []}):
                if failure:
                    with patch.object(client, "call", side_effect=TimeoutError("private details")):
                        case.cancel_when_dispatched(client, "au-1", observed)
                else:
                    case.cancel_when_dispatched(client, "au-1", observed)
            self.assertEqual(client.posts, [])
            self.assertFalse(observed.get("interrupted"))
            self.assertNotIn("private details", json.dumps(observed))

    def test_reconcile_distinguishes_completed_from_unconfirmed_original(self):
        unknown = {"steps": [{"model_request_id": "target", "status": "unknown"}],
                   "budget": {"used": 0, "reserved": 1}}
        measured = {"input_tokens": 9, "output_tokens": 2}
        completed = {"steps": [{"model_request_id": "target", "status": "used", "usage": measured}],
                     "budget": {"used": 1, "reserved": 0}}
        self.assertEqual(interrupted.reconciliation_problems(unknown, "target", {"called": True, "usage": None}), [])
        self.assertEqual(interrupted.reconciliation_problems(completed, "target", {"called": True, "usage": measured}), [])
        self.assertTrue(interrupted.reconciliation_problems(unknown, "target", {"called": True, "usage": measured}))
        self.assertTrue(interrupted.reconciliation_problems(completed, "target", {"called": True, "usage": None}))
        self.assertTrue(interrupted.reconciliation_problems(unknown, "another", {"called": True, "usage": None}))

    def test_bounded_driver_exercises_actual_http_document_and_candidate_download(self):
        from tests.model_access_support import ModelAccessCase
        from ai_union.work_transport import ModeldWorkTransport
        original_transport = ModeldWorkTransport.chat
        case = bounded.RealBoundedAcceptanceTests()
        count = 0
        def model(channel, package, messages, tools):
            nonlocal count
            count += 1
            if count == 1:
                return {"content": None, "tool_calls": [{"id": "read-1", "type": "function", "function": {
                    "name": "read_document", "arguments": '{"path":"brief.md"}'}}]}, {"input_tokens": 10, "output_tokens": 5}
            document = json.loads(next(m["content"] for m in messages if m["role"] == "tool"))
            return {"content": document["content"], "tool_calls": []}, {"input_tokens": 20, "output_tokens": 7}
        try:
            ModelAccessCase.setUp(case)
            with patch.object(case, "grant", return_value=("grant-a", 1)), \
                    patch.object(bounded, "MODEL", "model-a"), \
                    patch.object(bounded, "modeld_factory", return_value=lambda au, c: ModeldWorkTransport(None, au, c)), \
                    patch.object(ModeldWorkTransport, "chat", model), redirect_stdout(io.StringIO()):
                try:
                    case.test_one_work_uses_at_most_two_calls_and_reports_usage_without_cost()
                finally:
                    # Undo the driver's observer before its outer fake is restored.
                    case.doCleanups()
            self.assertEqual(count, 2)
            self.assertIs(ModeldWorkTransport.chat, original_transport)
        finally:
            case.doCleanups()


if __name__ == "__main__":
    unittest.main()
