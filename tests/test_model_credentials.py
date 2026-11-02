"""Credential references: an environment variable name may be stored, its value may not."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from ai_union.console import Console
from ai_union.engine import Rejected
from ai_union.model_api import APIExecutor, list_connections, resolve_connection
from tests.support import CHARTER, RESOURCES

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "examples/fixture.json").read_text(encoding="utf-8"))
VARIABLE = "UNION_MODEL_TEST_KEY"
VALUE = "env-key-value-PRIVATE-never-persisted"


class CredentialReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.saved = os.environ.pop(VARIABLE, None)
        self.addCleanup(self.restore)
        self.app = Console(Path(self.temp.name) / "console", fixture=FIXTURE)
        self.addCleanup(self.app.close)
        self.board = self.app.new_session("board", platform_admin=True)
        self.counter = 0
        receipt = self.command("create", {"name": "credential test", "goal": "test credential references",
                                          "board_name": "test board", "charter": CHARTER, "resources": RESOURCES})
        self.org = receipt["organization_id"]
        self.e = self.app.engine(self.board, self.org)
        self.base = {"name": "Env connection", "base_url": "https://example.invalid/v1", "model": "test-model",
                     "token_limit_field": "max_tokens", "max_output_tokens": 2048,
                     "timeout_seconds": 30, "enabled": True}

    def restore(self):
        os.environ.pop(VARIABLE, None)
        if self.saved is not None:
            os.environ[VARIABLE] = self.saved

    def command(self, kind, data):
        self.counter += 1
        return self.app.command(self.board, {"id": f"credential-command-{self.counter}", "kind": kind,
                                             "organization_id": getattr(self, "org", None),
                                             "base_version": self.e.state()["version"] if hasattr(self, "e") else None,
                                             "data": data})

    def bind(self):
        return self.command("api_binding", {"connection_id": "primary", "reason": "bind for resolution"})

    def configure(self, config=None, **extra):
        data = {"connection_id": "primary", "config": config or dict(self.base, api_key_env=VARIABLE),
                "reason": "environment reference"}
        data.update(extra)
        return self.command("api_connection", data)

    def test_environment_reference_does_not_persist_the_value(self):
        os.environ[VARIABLE] = VALUE
        receipt = self.configure()
        self.assertEqual(receipt["status"], "succeeded", receipt.get("message"))
        self.assertTrue(receipt["connection"]["has_api_key"])
        self.assertEqual(receipt["connection"]["key_source"], "env")
        with self.e.read_transaction() as cx:
            self.assertEqual(cx.execute("SELECT api_key FROM model_connections").fetchone()[0], "")
            stored = [row[0] for row in cx.execute("SELECT payload FROM commands")]
        exposed = json.dumps([receipt, self.e.state(), self.e.events(), stored,
                              self.app.model_connections(self.board, self.org)], ensure_ascii=False)
        self.assertNotIn(VALUE, exposed)

    def test_projection_reports_the_source_not_the_value(self):
        os.environ[VARIABLE] = VALUE
        self.configure()
        listed = list_connections(self.e)[0]
        self.assertEqual(listed["key_source"], "env")
        self.assertTrue(listed["has_api_key"])
        self.assertEqual(listed["config"]["api_key_env"], VARIABLE)
        self.assertNotIn(VALUE, json.dumps(listed, ensure_ascii=False))

    def test_resolution_returns_the_environment_value(self):
        os.environ[VARIABLE] = VALUE
        self.configure()
        self.bind()
        self.assertEqual(resolve_connection(self.e)["api_key"], VALUE)

    def test_missing_variable_is_reported_by_name_without_a_value(self):
        receipt = self.configure()
        self.assertEqual(receipt["status"], "succeeded", receipt.get("message"))
        self.assertFalse(list_connections(self.e)[0]["has_api_key"])
        self.bind()
        with self.assertRaises(Rejected) as caught:
            resolve_connection(self.e)
        self.assertIn(VARIABLE, str(caught.exception))

    def test_inline_key_still_persists_and_reports_inline(self):
        receipt = self.configure(dict(self.base), api_key="inline-key-PRIVATE")
        self.assertEqual(receipt["status"], "succeeded", receipt.get("message"))
        self.assertEqual(receipt["connection"]["key_source"], "inline")
        with self.e.read_transaction() as cx:
            self.assertEqual(cx.execute("SELECT api_key FROM model_connections").fetchone()[0], "inline-key-PRIVATE")

    def test_inline_key_and_reference_are_mutually_exclusive(self):
        os.environ[VARIABLE] = VALUE
        receipt = self.configure(api_key="inline-key-PRIVATE")
        self.assertEqual(receipt["status"], "rejected")
        self.assertIn("二选一", receipt["message"])

    def test_invalid_variable_name_is_rejected(self):
        for name in ("1BAD", "has space", "with-dash", "", "x" * 65):
            with self.subTest(name=name):
                receipt = self.configure(dict(self.base, api_key_env=name))
                self.assertEqual(receipt["status"], "rejected")

    def test_endpoint_change_is_allowed_when_reference_is_given(self):
        os.environ[VARIABLE] = VALUE
        self.assertEqual(self.configure()["status"], "succeeded")
        moved = dict(self.base, base_url="https://other.invalid/v1", api_key_env=VARIABLE)
        self.assertEqual(self.configure(moved)["status"], "succeeded")

    def test_endpoint_change_without_any_credential_is_still_rejected(self):
        self.assertEqual(self.configure(reason="first")["status"], "succeeded")
        moved = dict(self.base, base_url="https://other.invalid/v1")
        self.assertEqual(self.configure(moved)["status"], "rejected")

    def test_environment_value_cannot_be_pasted_into_reason(self):
        os.environ[VARIABLE] = VALUE
        self.configure()
        with self.assertRaises(Rejected) as caught:
            self.command("api_binding", {"connection_id": "primary", "reason": "pasted " + VALUE})
        self.assertNotIn(VALUE, str(caught.exception))

    def test_executor_receives_the_resolved_key(self):
        os.environ[VARIABLE] = VALUE
        self.configure()
        self.bind()
        executor = APIExecutor(self.e.root, resolve_connection(self.e))
        self.assertEqual(executor.connection["api_key"], VALUE)
        self.assertEqual(executor.metadata["connection_id"], "primary")


if __name__ == "__main__":
    unittest.main()
