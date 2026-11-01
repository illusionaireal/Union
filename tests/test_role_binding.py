"""Role-scoped connections: inheritance, availability fallback and explicit mapping."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from ai_union.console import Console
from ai_union.engine import Rejected
from ai_union.model_api import MAX_FALLBACKS, ROLE_BY_KIND, ROLES, resolve_connection, resolve_roles
from tests.support import CHARTER, RESOURCES

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "examples/fixture.json").read_text(encoding="utf-8"))
ABSENT = "UNION_TEST_ABSENT_KEY"


class RoleBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.saved = os.environ.pop(ABSENT, None)
        self.addCleanup(self.restore)
        self.app = Console(Path(self.temp.name) / "console", fixture=FIXTURE)
        self.addCleanup(self.app.close)
        self.board = self.app.new_session("board")
        self.counter = 0
        receipt = self.command("create", {"name": "role test", "goal": "test role bindings",
                                          "board_name": "test board", "charter": CHARTER, "resources": RESOURCES})
        self.org = receipt["organization_id"]
        self.e = self.app.engine(self.board, self.org)
        self.configure("primary", "a.invalid", enabled=True, key="primary-key")
        self.configure("secondary", "b.invalid", enabled=True, key="secondary-key")
        self.configure("disabled", "c.invalid", enabled=False, key="disabled-key")
        self.configure("nokey", "d.invalid", enabled=True, api_key_env=ABSENT)

    def restore(self):
        os.environ.pop(ABSENT, None)
        if self.saved is not None:
            os.environ[ABSENT] = self.saved

    def command(self, kind, data):
        self.counter += 1
        return self.app.command(self.board, {"id": f"role-command-{self.counter}", "kind": kind,
                                             "organization_id": getattr(self, "org", None),
                                             "base_version": self.e.state()["version"] if hasattr(self, "e") else None,
                                             "data": data})

    def configure(self, name, host, *, enabled, key=None, api_key_env=None):
        config = {"name": name, "base_url": f"https://{host}/v1", "model": name + "-model",
                  "token_limit_field": "max_tokens", "max_output_tokens": 1024,
                  "timeout_seconds": 30, "enabled": enabled}
        if api_key_env:
            config["api_key_env"] = api_key_env
            return self.command("api_connection", {"connection_id": name, "config": config, "reason": "role fixture"})
        return self.command("api_connection", {"connection_id": name, "config": config,
                                               "api_key": key, "reason": "role fixture"})

    def bind(self, connection_id, *, role=None, fallbacks=None):
        data = {"connection_id": connection_id, "reason": "role binding"}
        if role is not None:
            data["role"] = role
        if fallbacks is not None:
            data["fallbacks"] = fallbacks
        return self.command("api_binding", data)

    def test_role_inherits_the_default_binding(self):
        self.assertEqual(self.bind("primary")["status"], "succeeded")
        self.assertEqual(resolve_connection(self.e, role="worker")["id"], "primary")
        self.assertEqual(resolve_connection(self.e)["id"], "primary")

    def test_role_overrides_only_itself(self):
        self.bind("primary")
        self.assertEqual(self.bind("secondary", role="worker")["status"], "succeeded")
        self.assertEqual(resolve_connection(self.e, role="worker")["id"], "secondary")
        self.assertEqual(resolve_connection(self.e, role="planner")["id"], "primary")
        self.assertEqual(resolve_connection(self.e)["id"], "primary")

    def test_clearing_a_role_returns_to_inheritance(self):
        self.bind("primary")
        self.bind("secondary", role="worker")
        self.assertEqual(self.bind(None, role="worker")["status"], "succeeded")
        self.assertEqual(resolve_connection(self.e, role="worker")["id"], "primary")

    def test_unknown_role_is_rejected(self):
        self.assertEqual(self.bind("primary", role="intern")["status"], "rejected")

    def test_availability_fallback_skips_a_disabled_connection(self):
        self.bind("disabled", fallbacks=["secondary"])
        resolved = resolve_connection(self.e)
        self.assertEqual(resolved["id"], "secondary")
        self.assertEqual(resolved["fallback_from"], "disabled")

    def test_availability_fallback_skips_a_connection_without_credential(self):
        self.bind("nokey", fallbacks=["secondary"])
        self.assertEqual(resolve_connection(self.e)["id"], "secondary")

    def test_fallback_is_not_used_when_the_preferred_connection_works(self):
        self.bind("primary", fallbacks=["secondary"])
        resolved = resolve_connection(self.e)
        self.assertEqual(resolved["id"], "primary")
        self.assertNotIn("fallback_from", resolved)

    def test_all_unusable_reports_the_preferred_reason(self):
        self.bind("disabled", fallbacks=["nokey"])
        with self.assertRaises(Rejected) as caught:
            resolve_connection(self.e)
        self.assertIn("停用", str(caught.exception))

    def test_chain_bounds_and_duplicates_are_rejected(self):
        too_many = ["secondary", "disabled", "nokey", "primary"]
        self.assertGreater(len(too_many), MAX_FALLBACKS)
        self.assertEqual(self.bind("primary", fallbacks=too_many)["status"], "rejected")
        self.assertEqual(self.bind("primary", fallbacks=["secondary", "secondary"])["status"], "rejected")
        self.assertEqual(self.bind("primary", fallbacks=["primary"])["status"], "rejected")
        self.assertEqual(self.bind("primary", fallbacks=["absent-connection"])["status"], "rejected")

    def test_chain_is_recorded_on_the_binding_event(self):
        self.bind("primary", fallbacks=["secondary", "disabled"])
        events = [item for item in self.e.events() if item.get("kind") == "api_connection_bound"]
        self.assertEqual(events[-1]["data"]["fallbacks"], ["secondary", "disabled"])

    def test_resolve_roles_reports_every_role(self):
        self.bind("primary")
        self.bind("secondary", role="worker")
        resolved = resolve_roles(self.e)
        self.assertEqual(sorted(resolved), sorted(ROLES))
        self.assertEqual(resolved["worker"]["id"], "secondary")
        self.assertEqual(resolved["planner"]["id"], "primary")
        self.assertEqual(resolved["reviewer"]["id"], "primary")

    def test_resolve_roles_marks_an_unusable_role_as_none(self):
        self.bind("disabled", role="planner")
        self.assertIsNone(resolve_roles(self.e)["planner"])

    def test_package_kinds_map_to_roles_explicitly(self):
        self.assertEqual(ROLE_BY_KIND, {"work": "worker", "decision": "planner", "connection_test": None})

    def test_binding_requires_existing_connections(self):
        self.assertEqual(self.bind("primary", role="worker", fallbacks=["absent"])["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
