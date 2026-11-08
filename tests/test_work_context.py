"""S03 tool outputs must be inputs to the next decision, with durable provenance."""
import copy
import hashlib
import json
import unittest
import uuid
from unittest.mock import patch

from tests import test_core_work as support


def tool_call(name="read_document", arguments=None, call_id="read-1", content=None):
    return {"content": content, "tool_calls": [{"id": call_id, "type": "function", "function": {
        "name": name, "arguments": json.dumps(arguments if arguments is not None else {"path": "nested/a.md"})}}]}


class WorkContextTests(support.CoreWorkTests):
    def arrange_context(self):
        self.work_with_listing()
        root = self.prepare_materials()
        self.start_attempt()
        return root

    def successful_step(self):
        status, value, request = self.work_step()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertNotEqual(value["receipt"].get("model_outcome"), "unknown", value)
        return value["receipt"], request

    def test_tool_text_pairing_and_sources_drive_the_second_decision(self):
        root = self.arrange_context()
        nonce = "public-" + uuid.uuid4().hex + " 中文\r\n"
        raw = b"\xef\xbb\xbf" + nonce.encode("utf-8")
        (root / "nested/a.md").write_bytes(raw)
        owner = self
        calls = []

        class ReadingModel:
            def chat(self, package, messages, tools):
                calls.append(copy.deepcopy(messages))
                if len(calls) == 1:
                    return tool_call(), {}
                owner.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "tool"])
                owner.assertEqual(messages[2]["tool_calls"][0]["id"], messages[3]["tool_call_id"])
                result = json.loads(messages[3]["content"])
                owner.assertEqual(result["path"], "nested/a.md")
                owner.assertEqual(result["content"], nonce)
                owner.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
                owner.assertEqual(result["bytes"], len(raw))
                return {"content": result["content"], "tool_calls": []}, {}

        self.app.work.transport = ReadingModel()
        self.successful_step()
        before_answer = json.dumps(self.works(), ensure_ascii=False)
        self.assertNotIn(nonce.strip(), before_answer)
        self.assertNotIn(nonce.strip(), json.dumps(self.read(), ensure_ascii=False))
        self.successful_step()
        card = self.works()["works"][0]
        self.assertEqual(card["results"][0]["sources"], [card["tool_calls"][0]["step_ref"]])
        status, body, _ = self.result_content(card["results"][0]["id"])
        self.assertEqual(status, 200, body)
        self.assertEqual(body["content"], nonce)

    def test_listing_then_read_then_answer_uses_actual_filenames_and_keeps_prose_intermediate(self):
        root = self.arrange_context()
        name = "public-" + uuid.uuid4().hex + ".md"
        (root / name).write_text("source chosen from listing", encoding="utf-8")
        owner = self
        count = 0

        class ListingModel:
            def chat(self, package, messages, tools):
                nonlocal count
                count += 1
                if count == 1:
                    return tool_call("list_documents", {}, "list-1", "I will inspect the files."), {}
                outputs = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
                owner.assertTrue(outputs, "actual listing must reach the next model call")
                if count == 2:
                    selected = next(item for item in outputs[0]["documents"] if item.startswith("public-"))
                    return tool_call(arguments={"path": selected}, call_id="read-selected"), {}
                return {"content": outputs[-1]["content"], "tool_calls": []}, {}

        self.app.work.transport = ListingModel()
        status, value, _ = self.run_loop()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(value["receipt"]["turns"], 3)
        card = self.works()["works"][0]
        self.assertEqual(len(card["results"]), 1)
        self.assertEqual(card["results"][0]["sources"], [c["step_ref"] for c in card["tool_calls"]])

    def test_reopen_with_explicit_attempt_handover_uses_original_snapshot(self):
        root = self.arrange_context()
        original = (root / "nested/a.md").read_text(encoding="utf-8")
        self.with_transport(tool_call())
        self.successful_step()
        attempt = self.works()["works"][0]["attempts"][0]["id"]
        (root / "nested/a.md").write_text("later replacement", encoding="utf-8")
        self.stop()
        self.start()
        self.work_command(self.au_id, "finish_attempt", {"work_id": "work-overview", "attempt_id": attempt,
                          "outcome": "delivered", "reason": "previous bounded read was confirmed"})
        self.start_attempt()
        transport = self.with_transport({"content": "continued", "tool_calls": []})
        self.successful_step()
        tool_messages = [m for m in transport.calls[0]["messages"] if m["role"] == "tool"]
        self.assertTrue(tool_messages, "restart must retain the original tool result")
        self.assertEqual(json.loads(tool_messages[0]["content"])["content"], original)
        self.assertNotIn("later replacement", json.dumps(transport.calls))

    def test_corrupt_or_missing_context_refuses_before_any_dispatch(self):
        self.arrange_context()
        self.with_transport(tool_call())
        self.successful_step()
        directory, _ = self.app.governance.locate(self.au_id)
        with self.app.work.store.transaction(directory) as cx:
            table = cx.execute("SELECT name FROM sqlite_master WHERE name='work_model_turns'").fetchone()
            self.assertIsNotNone(table, "successful tool turn needs a private durable snapshot")
            cx.execute("UPDATE work_model_turns SET payload='{}'")
        transport = self.with_transport({"content": "must not run"})
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(transport.calls, [])
        with self.app.work.store.transaction(directory) as cx:
            cx.execute("DELETE FROM work_model_turns")
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(transport.calls, [])

    def test_unregistered_root_cannot_disclose_a_previously_read_snapshot(self):
        self.arrange_context()
        self.with_transport(tool_call())
        self.successful_step()
        (self.app.root / "document-roots.json").unlink()
        transport = self.with_transport({"content": "must not see old data"})
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(transport.calls, [])

    def test_rebinding_the_same_root_name_cannot_disclose_the_previous_roots_snapshot(self):
        root = self.arrange_context()
        self.with_transport(tool_call())
        self.successful_step()
        replacement = root.parent / "replacement-docs"
        replacement.mkdir()
        (self.app.root / "document-roots.json").write_text(json.dumps({
            "version": 1, "roots": {"project-docs": str(replacement)}}), encoding="utf-8")
        transport = self.with_transport({"content": "must not see original root"})
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(transport.calls, [])

    def test_current_charter_revocation_stops_context_dispatch(self):
        self.arrange_context()
        self.with_transport(tool_call())
        self.successful_step()
        charter = copy.deepcopy(self.read()["au"]["charter"])
        charter["allowed_tools"].remove("read_document")
        self.success("amend_charter", {"charter": charter, "reason": "withdraw document access"})
        transport = self.with_transport({"content": "must not see old data"})
        status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(transport.calls, [])

    def test_another_work_cannot_inherit_private_tool_messages(self):
        self.arrange_context()
        self.with_transport(tool_call())
        self.successful_step()
        attempt = self.works()["works"][0]["attempts"][0]["id"]
        self.work_command(self.au_id, "finish_attempt", {"work_id": "work-overview", "attempt_id": attempt,
                          "outcome": "delivered", "reason": "bounded read completed"})
        self.second_work()
        self.start_attempt("work-second")
        transport = self.with_transport({"content": "independent answer", "tool_calls": []})
        status, value, _ = self.work_step("work-second")
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual([m["role"] for m in transport.calls[0]["messages"]], ["system", "user"])

    def test_context_limit_refuses_without_truncation_or_dispatch(self):
        self.arrange_context()
        self.with_transport(tool_call())
        self.successful_step()
        before = self.works()["works"][0]
        transport = self.with_transport({"content": "must not run"})
        with patch("ai_union.adapters.work_context_store.MAX_CONTEXT_BYTES", 32):
            status, value, _ = self.work_step()
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertEqual(transport.calls, [])
        self.assertEqual(self.works()["works"][0], before)

    def test_native_assistant_context_survives_only_in_the_private_next_turn(self):
        self.arrange_context()
        first = tool_call()
        first["_native"] = {"au_id": self.au_id, "account_ref": "synthetic-account", "model_id": "model-a",
                            "upstream": "synthetic-upstream", "message": {"role": "assistant", "content": [
                                {"type": "reasoning", "text": "synthetic-private-native-context"},
                                {"type": "tool-call", "id": "read-1", "name": "read_document",
                                 "input": {"path": "nested/a.md"}}]}}
        self.with_transport(first)
        self.successful_step()
        self.assertNotIn("synthetic-private-native-context", json.dumps(self.read()))
        transport = self.with_transport({"content": "answer", "tool_calls": []})
        self.successful_step()
        assistant = next(m for m in transport.calls[0]["messages"] if m["role"] == "assistant")
        self.assertEqual(assistant.get("_native"), first["_native"])

    def test_automatic_tools_cannot_expand_the_works_mandate(self):
        self.saved()
        self.adopt_default()
        self.allow_listing()
        status, value, _ = self.work()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.prepare_materials()
        self.start_attempt()
        self.with_transport(tool_call("list_documents", {}))
        with patch("ai_union.application.work.documents.list_documents", return_value=[]) as listing:
            status, value, _ = self.work_step()
        listing.assert_not_called()
        self.assertEqual(value["receipt"]["status"], "rejected", value)

    def test_unpaired_or_excessive_tool_batch_never_reads_documents(self):
        self.arrange_context()
        batch = tool_call()["tool_calls"]
        for calls in (batch * 2, [dict(batch[0], id="call-" + str(i)) for i in range(11)]):
            with self.subTest(count=len(calls)):
                self.with_transport({"content": None, "tool_calls": calls})
                with patch("ai_union.application.work.documents.read_text", return_value=("must not read", "0" * 64, 13)) as reader:
                    status, value, _ = self.work_step()
                reader.assert_not_called()
                self.assertEqual(value["receipt"]["status"], "rejected", value)

    def test_context_and_step_roll_back_together_when_final_save_fails(self):
        self.arrange_context()
        self.with_transport(tool_call())
        before = self.works()["works"][0]
        request = {"id": str(uuid.uuid4()), "organization_id": self.au_id, "base_version": self.works()["version"],
                   "kind": "run_step", "data": {"work_id": "work-overview"}}
        with patch.object(self.app.work.store, "save", side_effect=OSError("injected save failure")):
            with self.assertRaises(OSError):
                self.app.work.run_step(self.token, request)
        self.assertEqual(self.works()["works"][0], before)
        directory, _ = self.app.governance.locate(self.au_id)
        with self.app.work.store.transaction(directory) as cx:
            if cx.execute("SELECT 1 FROM sqlite_master WHERE name='work_model_turns'").fetchone():
                self.assertEqual(cx.execute("SELECT count(*) FROM work_model_turns").fetchone()[0], 0)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkContextTests(name) for name in WorkContextTests.__dict__ if name.startswith("test_"))
