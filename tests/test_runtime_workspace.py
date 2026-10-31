"""Read-only workspace projections from fixture Engine states; no container runs."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_union import workspace
from ai_union.engine import Engine
from ai_union.observation import snapshot
from tests.support import decision, init, organization


class RuntimeWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "private-business-directory"
        self.directory.mkdir()
        self.config = {"directory": str(self.directory), "image": "sha256:" + "b" * 64,
                       "timeout_seconds": 30, "enabled": True}
        self.e = self.engine("org")

    def engine(self, name):
        engine = init(Path(self.temp.name) / name)
        charter = engine.charter()
        charter["allowed_tools"].append(workspace.TOOL)
        engine.amend("test-key", charter, "Fixture tool boundary")
        organization(engine)
        return engine

    def permission(self, engine, position_id, allowed):
        position = engine.state()["positions"][position_id]
        permissions = [p for p in position["permissions"] if p != workspace.TOOL]
        if allowed:
            permissions.append(workspace.TOOL)
        engine.apply_decision(decision(engine, [{"op": "update_position", "position_id": position_id,
            "title": position["title"], "mandate": position["mandate"], "permissions": permissions}]), "m1", "a1")

    def secondary(self, engine, first_allowed, selected_allowed):
        self.permission(engine, "p1", first_allowed)
        engine.apply_decision(decision(engine, [
            {"op": "create_position", "id": "p3", "title": "Fixture second responsibility",
             "mandate": "Fixture work", "permissions": ["produce_artifact"] + ([workspace.TOOL] if selected_allowed else [])},
            {"op": "assign", "id": "a3", "position_id": "p3", "member_id": "m1"},
            {"op": "create_work", "id": "a-secondary", "title": "Fixture selected work",
             "instruction": "Produce a fixture artifact", "position_id": "p3", "dependencies": []},
        ]), "m1", "a1")

    def persisted(self, engine):
        with engine.read_transaction() as cx:
            tables = [r["name"] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            grants = [dict(r) for r in cx.execute("SELECT * FROM workspace_grant")] if "workspace_grant" in tables else []
            commands = [dict(r) for r in cx.execute("SELECT * FROM workspace_commands")] if "workspace_commands" in tables else []
        return engine.state(), engine.events(), engine.runs(), tables, grants, commands

    def observe(self, engine, member_id="m1"):
        before = self.persisted(engine)
        result = None
        with patch.object(workspace, "run_container") as container:
            for reader in (engine, Engine(engine.root), engine):
                view = snapshot(reader)
                member = next(m for m in view["member_execution"] if m["member_id"] == member_id)
                if result is not None:
                    self.assertEqual(member, result)
                result = member
                self.assertEqual(view["budget"]["calls_reserved"], len(before[2]))
                public = json.dumps(view)
                self.assertNotIn(str(self.directory), public)
                self.assertNotIn(self.config["image"], public)
                self.assertNotIn("board_hash", public)
            container.assert_not_called()
        self.assertEqual(before, self.persisted(engine))
        return result

    def test_workspace_uses_selected_assignment_in_both_permission_directions(self):
        for first_allowed in (False, True):
            with self.subTest(first_allowed=first_allowed):
                engine = self.engine("multiple-" + str(first_allowed))
                self.secondary(engine, first_allowed, not first_allowed)
                workspace.configure(engine, "test-key", self.config, "Fixture host binding")
                member = self.observe(engine)
                self.assertEqual(member["assignment_ids"], ["a1", "a3"])
                self.assertEqual(member["current_work_id"], "a-secondary")
                self.assertEqual(member["workspace"], {"mode": "shared_business", "revision": 1,
                    "available": not first_allowed, "reason_codes": ["workspace_not_authorized"] if first_allowed else []})

    def test_workspace_without_current_work_does_not_choose_an_assignment(self):
        self.permission(self.e, "p1", True)
        workspace.configure(self.e, "test-key", self.config, "Fixture host binding")
        self.e.apply_decision(decision(self.e, [{"op": "cancel_work", "work_id": "w1"},
            {"op": "cancel_work", "work_id": "w2"}]), "m1", "a1")
        member = self.observe(self.e)
        self.assertIsNone(member["current_work_id"])
        self.assertEqual(member["workspace"]["available"], False)
        self.assertEqual(member["workspace"]["reason_codes"], ["no_current_work"])
        self.e.apply_decision(decision(self.e, [{"op": "handoff", "position_id": "p1", "member_id": "m2", "assignment_id": "a3"}]), "m1", "a1")
        self.assertEqual(self.observe(self.e)["workspace"]["reason_codes"], ["no_active_assignment"])

    def test_disabled_workspace_reason_precedes_missing_current_work(self):
        self.permission(self.e, "p1", True)
        workspace.configure(self.e, "test-key", self.config, "Fixture host binding")
        workspace.disable(self.e, "test-key", "Fixture disable")
        for operations in ([], [{"op": "cancel_work", "work_id": "w1"}]):
            if operations:
                self.e.apply_decision(decision(self.e, operations), "m1", "a1")
            self.assertEqual(self.observe(self.e)["workspace"], {"mode": "shared_business", "revision": 2,
                "available": False, "reason_codes": ["workspace_disabled"]})

    def test_current_position_and_charter_revocation_are_observed(self):
        self.permission(self.e, "p1", True)
        workspace.configure(self.e, "test-key", self.config, "Fixture host binding")
        self.assertTrue(self.observe(self.e)["workspace"]["available"])
        self.permission(self.e, "p1", False)
        self.assertEqual(self.observe(self.e)["workspace"]["reason_codes"], ["workspace_not_authorized"])
        self.permission(self.e, "p1", True)
        self.assertTrue(self.observe(self.e)["workspace"]["available"])
        charter = self.e.charter()
        charter["allowed_tools"].remove(workspace.TOOL)
        self.e.amend("test-key", charter, "Fixture charter revocation")
        self.assertEqual(self.observe(self.e)["workspace"]["reason_codes"], ["workspace_not_authorized"])

    def test_handoff_uses_new_owners_work_assignment_not_their_other_position(self):
        self.permission(self.e, "p1", True)
        workspace.configure(self.e, "test-key", self.config, "Fixture host binding")
        self.e.begin_work("w1", "fixture")
        # a0 sorts ahead of a2, so the former first-assignment algorithm chooses p2.
        self.e.apply_decision(decision(self.e, [
            {"op": "handoff", "position_id": "p2", "member_id": "m2", "assignment_id": "a0"},
            {"op": "handoff", "position_id": "p1", "member_id": "m2", "assignment_id": "a4"},
        ]), "m1", "a1")
        member = self.observe(self.e, "m2")
        self.assertEqual(member["current_work_id"], "w1")
        self.assertEqual(member["work_state"], "blocked")
        self.assertTrue(member["workspace"]["available"])
        self.assertEqual(self.observe(self.e)["workspace"]["reason_codes"], ["no_active_assignment"])

    def test_permission_summary_is_not_a_promise_that_commands_can_run(self):
        self.permission(self.e, "p1", True)
        workspace.configure(self.e, "test-key", self.config, "Fixture host binding")
        self.assertTrue(self.observe(self.e)["workspace"]["available"])
        self.e.set_paused(True)
        self.assertTrue(self.observe(self.e)["workspace"]["available"])
        self.e.set_paused(False)
        package = self.e.begin_work("w1", "fixture")
        self.assertTrue(workspace.available(self.e, package))
        self.e.set_paused(True)
        self.assertTrue(self.observe(self.e)["workspace"]["available"])
        self.assertFalse(workspace.available(self.e, package))

    def test_legacy_unconfigured_workspace_read_does_not_create_tables(self):
        member = self.observe(self.e)
        self.assertEqual(member["workspace"], {"mode": "virtual_only", "revision": None,
            "available": False, "reason_codes": ["workspace_unconfigured"]})


if __name__ == "__main__":
    unittest.main()
