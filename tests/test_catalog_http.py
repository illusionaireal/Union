"""Exercise S01a at the existing HTTP boundary and preserve legacy creation."""
import json
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import unittest

from tests import test_catalog_integrity, test_company, test_http
from tests.support import CHARTER, RESOURCES


class CatalogHTTPTests(unittest.TestCase):
    setUp = test_http.HTTPTests.setUp
    request = test_http.HTTPTests.request
    create = test_http.HTTPTests.create

    def test_wrong_mapping_returns_409_without_reading_or_mutating_the_other_au(self):
        au_a = self.create()
        create_b = test_catalog_integrity.CatalogIntegrityTests.creation("private-B")
        status, body, _ = self.request("POST", "/api/commands", create_b)
        self.assertEqual(status, 200)
        au_b = body["receipt"]["organization_id"]
        engine_b = self.app.engine(self.board, au_b)
        before = test_catalog_integrity.CatalogIntegrityTests.contents(engine_b)
        folders = {row["id"]: row["folder"] for row in self.app.organizations()}

        def restore():
            with self.app.catalog() as cx:
                cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folders[au_a], au_a))

        self.addCleanup(restore)
        with self.app.catalog() as cx:
            cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folders[au_b], au_a))
        self.cookie = self.server.cookie_name + "=" + self.app.new_session("board", organizations=[au_a])
        event = {"id": "must-not-reach-B", "organization_id": au_a, "base_version": 0,
                 "kind": "event", "data": {"event_id": "wrong-A", "kind": "opinion",
                                          "content": "A input", "source": "fixture", "simulated": True}}
        for method, path, data in (("GET", "/api/session", None),
                                   ("GET", "/api/snapshot?organization_id=" + au_a, None),
                                   ("POST", "/api/commands", event)):
            with self.subTest(method=method, path=path):
                status, body, _ = self.request(method, path, data)
                self.assertEqual(status, 409)
                self.assertIn("核对", body["error"])
                for private in ("private-B", str(engine_b.root), "board_hash", "board.key"):
                    self.assertNotIn(private, json.dumps(body, ensure_ascii=False))
        self.assertEqual(test_catalog_integrity.CatalogIntegrityTests.contents(engine_b), before)

        self.cookie = self.server.cookie_name + "=" + self.app.new_session("observer", organizations=[au_b])
        status, body, _ = self.request("GET", "/api/session")
        self.assertEqual(status, 200)
        self.assertEqual(body["organizations"], [{"id": au_b, "name": "private-B", "profile": "legacy_v0"}])
        self.assertEqual(self.request("GET", "/api/snapshot?organization_id=" + au_b)[0], 200)
        self.cookie = self.server.cookie_name + "=" + self.board
        status, body, _ = self.request("GET", "/api/receipts?id=create-http")
        self.assertEqual(status, 200)
        self.assertEqual(body["receipt"]["organization_id"], au_a)
        restore()
        status, body, _ = self.request("GET", "/api/snapshot?organization_id=" + au_a)
        self.assertEqual(status, 200)
        self.assertEqual(body["organization"]["id"], au_a)

    def test_registration_failure_queries_the_original_http_receipt_without_an_au_id(self):
        original = self.app.catalog
        calls = 0

        @contextmanager
        def fail_registration():
            nonlocal calls
            calls += 1
            with original() as cx:
                yield cx
                if calls == 2:
                    raise sqlite3.OperationalError("fixture registration failure")

        command = test_catalog_integrity.CatalogIntegrityTests.creation("unknown-http")
        with patch.object(self.app, "catalog", fail_registration):
            status, body, _ = self.request("POST", "/api/commands", command)
        self.assertEqual(status, 200)
        receipt = body["receipt"]
        self.assertEqual(receipt["status"], "unknown")
        self.assertIsNotNone(receipt["organization_id"])
        status, body, _ = self.request("GET", "/api/receipts?id=" + command["id"])
        self.assertEqual(status, 200)
        self.assertEqual(body["receipt"], receipt)
        self.assertEqual(self.request("POST", "/api/commands", command)[1]["receipt"], receipt)
        self.assertEqual(self.app.organizations(), [])

    def test_legacy_controller_and_company_creation_keep_their_versions(self):
        for name, extra, version in (("controller", {"controller_ref": {"principal_id": "external-org:test", "display_name": "fixture"}}, 1),
                                     ("company", {"company": test_company.CONFIG}, 0)):
            command = test_catalog_integrity.CatalogIntegrityTests.creation(name)
            charter = CHARTER | {"allowed_operations": sorted(set(CHARTER["allowed_operations"]) | {"submit_chapter", "review_cycle"})}
            command["data"] = command["data"] | extra | {"charter": charter}
            status, body, _ = self.request("POST", "/api/commands", command)
            self.assertEqual(status, 200)
            receipt = body["receipt"]
            self.assertEqual(receipt["status"], "succeeded")
            self.assertIsNone(receipt["base_version"])
            self.assertEqual(self.request("POST", "/api/commands", command)[1]["receipt"], receipt)
            state = self.app.engine(self.board, receipt["organization_id"]).state()
            self.assertEqual((state["version"], state["charter_version"], state["policy_version"]), (version, 1, 0))
            self.assertEqual(state["members"], {})
            if name == "company":
                self.assertEqual(state["company"]["target_cycles"], 3)

    def test_console_resource_limits_and_broader_cli_resources_remain_distinct(self):
        limits = RESOURCES | {"max_cost": 1.25, "cost_reserve_per_call": 0.25}
        command = test_catalog_integrity.CatalogIntegrityTests.creation("console-cost")
        command["data"] = command["data"] | {"resources": limits}
        status, body, _ = self.request("POST", "/api/commands", command)
        self.assertEqual(status, 200)
        self.assertEqual(body["receipt"]["status"], "rejected")
        self.assertEqual(self.app.organizations(), [])

        for index, resources in enumerate((RESOURCES | {"max_calls": True}, RESOURCES | {"max_calls": 10001},
                                            RESOURCES | {"timeout_seconds": 0}, RESOURCES | {"timeout_seconds": 3601})):
            request = test_catalog_integrity.CatalogIntegrityTests.creation("bad-resource-" + str(index))
            request["data"] = request["data"] | {"resources": resources}
            self.assertEqual(self.request("POST", "/api/commands", request)[1]["receipt"]["status"], "rejected")

        charter_file = self.app.root / "charter.json"
        resources_file = self.app.root / "resources.json"
        charter_file.write_text(json.dumps(CHARTER), encoding="utf-8")
        resources_file.write_text(json.dumps(limits), encoding="utf-8")
        directory = self.app.root / "organizations" / "cli-cost"
        completed = subprocess.run([sys.executable, "-m", "ai_union", "--root", str(directory), "init",
                                    "--name", "legacy CLI", "--goal", "fixture", "--board-name", "fixture",
                                    "--charter", str(charter_file), "--resources", str(resources_file)],
                                   cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
                                   encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        oid = json.loads(completed.stdout)["organization_id"]
        with self.app.catalog() as cx:
            cx.execute("INSERT INTO organizations(id,folder) VALUES(?,?)", (oid, "organizations/cli-cost"))
        self.assertEqual(self.app.engine(self.board, oid).state()["resources"], limits)


if __name__ == "__main__":
    unittest.main()
