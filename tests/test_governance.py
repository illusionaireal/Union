"""Adoption and activation use real HTTP and preserve original creation facts."""
from contextlib import closing
import copy
import json
import sqlite3
import uuid

from tests.governance_support import GovernanceCase


class GovernanceAdoptionTests(GovernanceCase):
    def test_adoption_and_activation_keep_initial_identity_and_creation_bytes(self):
        self.prepare()
        original = self.app.creation.catalog.intent_for_au(self.au_id)
        with closing(sqlite3.connect(self.database())) as cx:
            initial_state = cx.execute("SELECT data FROM state").fetchone()[0]
            initial_charter = cx.execute("SELECT data FROM charters WHERE version=1").fetchone()[0]
            initial_adoption = cx.execute("SELECT * FROM creation_adoptions").fetchall()
        receipt, _ = self.success("adopt_governance", {"config": self.config(), "reason": "Adopt explicit program"})
        adopted = self.read()
        self.assertEqual(adopted["au"]["schema_version"], 2)
        self.assertEqual(adopted["governance_status"], "prepared")
        self.assertEqual(adopted["au"]["governance"]["current_principal_id"], self.principal)
        self.assertEqual(adopted["history"][0]["command_id"], receipt["id"])
        self.success("activate_governance", {"reason": "Ready for internal records"})
        active = self.read()
        self.assertEqual(active["governance_status"], "active")
        self.assertEqual(active["access"]["principal_id"], self.principal)
        self.assertEqual(active["access"]["service_instance"], self.app.instance)
        self.assertTrue(active["capabilities"]["local_submission"])
        self.assertFalse(active["capabilities"]["autonomous_business"])
        self.assertEqual((active["au"]["autonomy_state"], active["au"]["resource_state"]), ("inactive", "planned"))
        self.assertEqual(self.app.creation.catalog.intent_for_au(self.au_id), original)
        with closing(sqlite3.connect(self.database())) as cx:
            self.assertEqual(cx.execute("SELECT state,charter FROM governance_origin").fetchone(), (initial_state, initial_charter))
            self.assertEqual(cx.execute("SELECT * FROM creation_adoptions").fetchall(), initial_adoption)
            self.assertEqual(cx.execute("SELECT data FROM charters WHERE version=1").fetchone()[0], initial_charter)
        old = {"id": "legacy-attempt", "organization_id": self.au_id, "base_version": active["au"]["version"], "kind": "start", "data": {}}
        self.assertEqual(self.request("/api/commands", old)[0], 409)
        self.stop()
        self.start()
        self.assertEqual(self.read()["au"], active["au"])
        self.assertEqual(self.request("/api/v1/receipts?id=v1-create")[1]["receipt"], json.loads(original["receipt"]))

    def test_incomplete_unknown_or_untrusted_governance_never_upgrades_the_prepared_au(self):
        self.prepare()
        cases = []
        for field in ("final_decision_principal_id", "reserved_matters", "unavailability"):
            case = self.config()
            del case[field]
            cases.append(case)
        case = self.config(); case["unavailability"]["mode"] = "prompt_decides"; cases.append(case)
        case = self.config(); case["final_decision_principal_id"] = str(uuid.uuid4()); cases.append(case)
        case = self.config(); case["reserved_matters"] = ["charter"]; cases.append(case)
        case = self.config(); case["extra_authority"] = True; cases.append(case)
        before = self.dump()
        for config in cases:
            with self.subTest(config=config):
                status, result, _ = self.command("adopt_governance", {"config": config, "reason": "Candidate"})
                self.assertEqual(status, 400, result)
                self.assertEqual(self.dump(), before)
        host = self.app.new_session("board", platform_admin=True)
        self.assertEqual(self.command("adopt_governance", {"config": self.config(), "reason": "Host cannot bind"}, token=host, version=0)[0], 403)
        self.assertEqual(self.dump(), before)

    def test_successor_must_confirm_before_activation(self):
        self.prepare()
        successor = self.participant("successor")
        outsider = self.participant("outsider")
        self.success("adopt_governance", {"config": self.config(successor[1]), "reason": "Preselect recovery"})
        self.reject("activate_governance", {"reason": "Not yet confirmed"})
        self.assertEqual(self.read()["governance_status"], "prepared")
        self.assertEqual(self.command("acknowledge_recovery", {"reason": "Wrong subject"}, token=outsider[0], version=1)[0], 403)
        self.success("acknowledge_recovery", {"reason": "I accept this bounded duty"}, token=successor[0])
        self.success("activate_governance", {"reason": "Confirmed program"})
        self.assertEqual(self.read()["governance_status"], "active")

    def test_partial_adoption_failure_leaves_original_prepared_records_only(self):
        self.prepare()
        with closing(sqlite3.connect(self.database())) as cx, cx:
            cx.execute("CREATE TRIGGER fail_adoption BEFORE UPDATE ON state BEGIN SELECT RAISE(ABORT, 'controlled failure'); END")
        before = self.dump()
        status, result, request = self.command("adopt_governance", {"config": self.config(), "reason": "Atomic adoption"})
        self.assertEqual((status, result.get("code")), (503, "storage_unavailable"), result)
        self.assertEqual(self.dump(), before)
        with closing(sqlite3.connect(self.database())) as cx, cx:
            cx.execute("DROP TRIGGER fail_adoption")
        status, result, _ = self.request("/api/v1/governance/commands", request)
        self.assertEqual(status, 200, result)
        self.assertEqual(result["receipt"]["status"], "succeeded")

    def test_initial_version_rejection_retains_original_receipt_without_adopting_schema_two(self):
        self.prepare()
        original = self.read()["au"]
        status, value, request = self.command("adopt_governance", {"config": self.config(), "reason": "Check original version"}, version=1, request_id="first-stale")
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected")
        self.assertEqual(self.read()["au"], original)
        path = f"/api/v1/governance/receipts?organization_id={self.au_id}&id=first-stale"
        self.assertEqual(self.request(path)[1]["receipt"], value["receipt"])
        self.assertEqual(self.request("/api/v1/governance/commands", request)[1]["receipt"], value["receipt"])
        changed = copy.deepcopy(request); changed["base_version"] = 0
        self.assertEqual(self.request("/api/v1/governance/commands", changed)[0], 409)
        self.success("adopt_governance", {"config": self.config(), "reason": "A reviewed fresh request"})
        self.assertEqual(self.request(path)[1]["receipt"], value["receipt"])
