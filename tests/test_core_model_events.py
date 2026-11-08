"""U-097: original persisted events via actual core HTTP, never new inference."""
import copy
import json
import time
import sqlite3
from contextlib import closing
from unittest.mock import patch
from urllib.parse import urlencode

from tests.model_access_support import ModelAccessCase


class CoreModelEventsTests(ModelAccessCase):
    def ready(self):
        self.saved()
        self.allow_documents()
        self.resource_grant(6)

    @staticmethod
    def event(request_id, seq, kind, payload):
        return {"request_id": request_id, "seq": seq, "type": kind,
                "payload": payload, "created_at": "2026-11-09"}

    def seeded(self, count=3):
        self.ready()
        def events(request_id, au_id, after=0):
            values = [self.event(request_id, i, "text_delta", {"text": "片段" + str(i)})
                      for i in range(1, count + 1)]
            values += [self.event(request_id, count + 1, "native_event", {"text": "private-native-canary"}),
                       self.event(request_id, count + 2, "tool_call_complete",
                                  {"name": "read_document", "arguments": "private-tool-canary"})]
            return {"events": [v for v in values if v["seq"] > after][:500]}
        with patch.object(self.provider, "events", side_effect=events):
            receipt, _ = self.start_check()
            check = self.wait_for("checks", receipt["check_id"])
        self.check_id, self.attempt_id = check["id"], check["attempts"][0]["id"]
        return check

    def events(self, after=0, **kwargs):
        params = {"organization_id": self.au_id, "check_id": self.check_id,
                  "attempt_id": self.attempt_id, "after": str(after)}
        params.update(kwargs.pop("params", {}))
        return self.request("/api/v1/models/events?" + urlencode(params), **kwargs)

    def test_original_event_projection_is_read_only_private_and_survives_restart(self):
        self.seeded()
        before, posts = self.dump(), copy.deepcopy(self.provider.posts)
        status, value, _ = self.events()
        self.assertEqual(status, 200, value)
        self.assertEqual(value["protocol"], "core.model-events.v1")
        self.assertEqual(value["access"]["principal_id"], self.principal)
        self.assertEqual(value["access"]["service_instance"], self.app.instance)
        self.assertEqual((value["check_id"], value["attempt_id"]), (self.check_id, self.attempt_id))
        self.assertEqual(value["events"], [
            {"seq": i, "type": "text_delta", "text": "片段" + str(i)} for i in range(1, 4)
        ] + [{"seq": 5, "type": "tool_call_complete", "name": "read_document"}])
        self.assertNotIn("private-", json.dumps(value))
        self.assertEqual((value["cursor"], value["last_seq"], value["has_more"]), (5, 5, False))
        self.assertEqual(self.events(5)[1]["events"], [])
        self.stop(); self.start()
        self.assertEqual(self.events()[1]["events"], value["events"])
        self.assertEqual(self.provider.posts, posts)
        self.assertEqual(self.dump(), before)

    def test_pagination_uses_original_sequences_and_repeated_gets_never_dispatch(self):
        self.seeded(501)
        posts = len(self.provider.posts)
        status, first, _ = self.events()
        self.assertEqual(status, 200, first)
        self.assertEqual((first["cursor"], first["has_more"]), (500, True))
        self.assertEqual(self.events()[1], first)
        second = self.events(500)[1]
        self.assertEqual([e["seq"] for e in second["events"]], [501, 503])
        self.assertEqual((second["cursor"], second["has_more"]), (503, False))
        self.assertEqual(len(self.provider.posts), posts)

    def test_stream_scope_denies_outsider_wrong_check_and_changed_grant(self):
        self.seeded()
        outsider, _ = self.participant("stream-outsider")
        self.assertEqual(self.events(token=outsider)[0], 403)
        self.assertEqual(self.events(params={"check_id": "unrelated-check"})[0], 403)
        self.assertEqual(self.events(params={"attempt_id": "unrelated-attempt"})[0], 403)
        self.provider.revoked = True
        self.assertEqual(self.events()[0], 403)
        self.provider.revoked = False
        self.provider.grant_revision += 1
        self.assertEqual(self.events()[0], 403)

    def test_invalid_cursor_is_rejected_and_never_creates_a_record(self):
        self.seeded()
        before = self.dump()
        for after in (-1, "wat", "1.2", 100000):
            self.assertEqual(self.events(after)[0], 400)
        self.assertEqual(self.dump(), before)

    def test_current_role_is_rechecked_after_model_grant_lookup(self):
        self.seeded()
        successor, principal = self.participant("stream-successor")
        self.success("nominate_governor", {"principal_id": principal, "reason": "handover"})
        self.assertEqual(self.events(token=successor)[0], 403, "nomination does not grant partial-output access")
        original = self.provider.call
        def handover(method, path, *args, **kwargs):
            value = original(method, path, *args, **kwargs)
            if path.startswith("/v1/grants/"):
                self.success("accept_governance", {"reason": "accept"}, token=successor)
            return value
        with patch.object(self.provider, "call", side_effect=handover):
            self.assertEqual(self.events()[0], 403)

    def test_running_attempt_exposes_saved_prefix_before_model_completion(self):
        self.ready()
        original = self.provider.request
        def running(request_id, au_id):
            result = original(request_id, au_id)
            return result if self.provider.result_state == "completed" else result | {"result": None}
        def events(request_id, au_id, after=0):
            return {"events": [self.event(request_id, 1, "text_delta", {"text": "仍在生成的正文"})] if after < 1 else []}
        self.provider.result_state = "running"
        try:
            with patch.object(self.provider, "request", side_effect=running), patch.object(self.provider, "events", side_effect=events):
                receipt, _ = self.start_check()
                self.check_id = receipt["check_id"]
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    check = next(c for c in self.models()["checks"] if c["id"] == self.check_id)
                    if check["attempts"] and check["attempts"][0]["usage"]["observed_through_seq"] == 1:
                        break
                    time.sleep(.02)
                self.attempt_id = check["attempts"][0]["id"]
                status, result, _ = self.events()
                self.assertEqual(status, 200, result)
                self.assertEqual(result["state"], "running")
                self.assertEqual(result["events"][0]["text"], "仍在生成的正文")
                self.assertEqual(len(self.provider.requests), 1)
                self.provider.result_state = "completed"
                self.wait_for("checks", self.check_id)
        finally:
            self.provider.result_state = "completed"

    def test_check_completion_metadata_during_read_does_not_revoke_same_connection(self):
        self.seeded()
        original = self.provider.call
        def completion(method, path, *args, **kwargs):
            value = original(method, path, *args, **kwargs)
            if path.startswith("/v1/grants/"):
                self.app.models.mutate(self.au_id, self.principal, "check_metadata_observed",
                    lambda state, charter, cx, principals:
                        state["model_access"]["connections"]["connection-a"].update(last_check=None))
            return value
        with patch.object(self.provider, "call", side_effect=completion):
            self.assertEqual(self.events()[0], 200)

    def test_private_result_identity_and_event_conflicts_fail_closed(self):
        self.seeded()
        with closing(sqlite3.connect(self.database())) as cx:
            raw = cx.execute("SELECT result FROM model_attempts WHERE id=?", (self.attempt_id,)).fetchone()[0]
        for kind in ("id", "digest", "event_scope", "conflict"):
            value = json.loads(raw)
            if kind == "id": value["id"] = "other-attempt"
            if kind == "digest": value["request_digest"] = "wrong"
            if kind == "event_scope": value["events"][0]["request_id"] = "other-attempt"
            if kind == "conflict": value["events"].append(value["events"][0] | {"payload": {"text": "wrong"}})
            with closing(sqlite3.connect(self.database())) as cx, cx:
                cx.execute("UPDATE model_attempts SET result=? WHERE id=?", (json.dumps(value), self.attempt_id))
            status, result, _ = self.events()
            self.assertEqual(status, 409, (kind, result))
            self.assertNotIn("events", result)

    def test_known_remote_revocation_and_local_disable_hide_content_without_erasing_facts(self):
        self.seeded()
        with closing(sqlite3.connect(self.database())) as cx, cx:
            value = json.loads(cx.execute("SELECT result FROM model_attempts WHERE id=?", (self.attempt_id,)).fetchone()[0])
            value["action_authorized"] = False
            cx.execute("UPDATE model_attempts SET result=? WHERE id=?", (json.dumps(value), self.attempt_id))
        before = self.dump()
        self.assertEqual(self.events()[0], 403)
        self.assertEqual(self.dump(), before)
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                             "enabled": False, "make_default": False})
        self.assertEqual(self.events()[0], 403)

    def test_empty_older_schema_does_not_create_private_tables_on_read(self):
        self.check_id, self.attempt_id = "absent-check", "absent-attempt"
        before = self.dump()
        self.assertEqual(self.read()["au"]["schema_version"], 2)
        self.assertEqual(self.events()[0], 403)
        self.assertEqual(self.dump(), before)
