"""Old rules authorize amendments and trusted, independently confirmed succession."""
from contextlib import closing
import copy
import json
import sqlite3
from unittest.mock import patch

from tests.governance_support import GovernanceCase


class GovernanceSuccessionTests(GovernanceCase):
    def test_old_charter_must_authorize_amendment_and_initial_creation_stays_immutable(self):
        self.prepare()
        self.activate()
        original = self.app.creation.catalog.intent_for_au(self.au_id)
        charter = copy.deepcopy(self.read()["au"]["charter"])
        charter.update(text="Explicitly freeze this amendment procedure", board_can_amend=False)
        receipt, request = self.success("amend_charter", {"charter": charter, "reason": "Adopt under old permitted rules"})
        before = self.read()["au"]
        self.assertEqual(before["charter_version"], 2)
        promoted = copy.deepcopy(charter)
        promoted.update(text="This new text authorizes itself", board_can_amend=True)
        self.reject("amend_charter", {"charter": promoted, "reason": "New text cannot approve itself"})
        self.assertEqual(self.read()["au"], before)
        self.assertEqual(self.app.creation.catalog.intent_for_au(self.au_id), original)
        self.assertEqual(self.request("/api/v1/governance/commands", request)[1]["receipt"], receipt)
        different = copy.deepcopy(request); different["data"]["reason"] = "Different bytes"
        status, value, _ = self.request("/api/v1/governance/commands", different)
        self.assertEqual((status, value["code"]), (409, "id_conflict"))

    def test_independent_acceptance_moves_current_authority_but_not_initial_root_or_receipts(self):
        self.prepare()
        self.activate()
        successor = self.participant("successor")
        stranger = self.participant("stranger")
        nomination, original_request = self.success("nominate_governor", {"principal_id": successor[1], "reason": "Transfer current governing duty"})
        version = self.read()["au"]["version"]
        self.assertEqual(self.command("accept_governance", {"reason": "Wrong target"}, token=stranger[0], version=version)[0], 403)
        accepted, _ = self.success("accept_governance", {"reason": "I accept the responsibility"}, token=successor[0])
        self.assertEqual(self.request("/api/v1/aus/" + self.au_id)[0], 403)
        current = self.read(successor[0])
        self.assertEqual(current["au"]["governance_root"]["governor_principal_id"], self.principal)
        self.assertEqual(current["au"]["governance"]["current_principal_id"], successor[1])
        self.assertEqual(current["governance_status"], "prepared")
        self.assertEqual(self.request("/api/session")[1]["organizations"], [])
        self.assertEqual(self.request("/api/v1/governance/commands", original_request)[1]["receipt"], nomination)
        path = f"/api/v1/governance/receipts?organization_id={self.au_id}&id={nomination['id']}"
        self.assertEqual(self.request(path)[1]["receipt"], nomination)
        self.assertEqual(self.request(path, token=successor[0])[0], 403)
        self.assertEqual(self.request("/api/v1/receipts?id=v1-create")[0], 200)
        self.assertEqual(self.request("/api/v1/receipts?id=v1-create", token=successor[0])[0], 403)
        config = self.config(); config["final_decision_principal_id"] = successor[1]
        self.success("configure_governance", {"config": config, "reason": "Confirm new term"}, token=successor[0])
        self.success("activate_governance", {"reason": "New governing term"}, token=successor[0])
        self.stop(); self.start()
        self.assertEqual(self.read(successor[0])["governance_status"], "active")
        self.assertEqual(self.request("/api/v1/aus/" + self.au_id)[0], 403)
        self.assertEqual(self.command("renew_governance", {"reason": "Old creator cannot act"}, version=accepted["version"])[0], 403)

    def test_policy_revision_cancels_old_nominations_and_recovery_confirmations(self):
        self.prepare()
        successor = self.participant("successor")
        self.activate(successor)
        self.success("nominate_governor", {"principal_id": successor[1], "reason": "Pending nomination"})
        self.success("amend_charter", {"charter": self.read()["au"]["charter"], "reason": "Review a fresh policy version"})
        self.assertIsNone(self.read()["au"]["governance"]["nomination"])
        self.assertIsNone(self.read()["au"]["governance"]["recovery_ack"])
        self.assertEqual(self.command("accept_governance", {"reason": "Stale nomination"}, token=successor[0])[0], 403)
        self.reject("activate_governance", {"reason": "Confirmation is stale"})
        self.success("acknowledge_recovery", {"reason": "Confirm revised policy"}, token=successor[0])
        self.success("activate_governance", {"reason": "Fresh confirmation"})

    def test_preconfirmed_successor_recovers_after_timeout_without_failed_governor_approval(self):
        self.prepare()
        successor = self.participant("successor")
        self.activate(successor)
        self.reject("recover_governance", {"reason": "Too early"}, token=successor[0])
        deadline = self.read()["au"]["governance"]["valid_until"]
        with patch("ai_union.application.governance.time.time", return_value=deadline + 1):
            self.assertEqual(self.read()["governance_status"], "unavailable")
            self.reject("renew_governance", {"reason": "Original term already expired"})
            self.success("recover_governance", {"reason": "Preaccepted timeout condition is met"}, token=successor[0])
            value = self.read(successor[0])
            self.assertEqual(value["au"]["governance"]["current_principal_id"], successor[1])
            self.assertEqual(value["governance_status"], "prepared")
            self.assertEqual(value["au"]["governance_root"]["creator_principal_id"], self.principal)
            self.assertEqual(self.request("/api/v1/aus/" + self.au_id)[0], 403)

    def test_single_subject_timeout_exit_cannot_be_renewed_back_into_authority(self):
        self.prepare()
        self.activate()
        before = self.read()["au"]
        self.success("renew_governance", {"reason": "Explicit timely renewal"})
        deadline = self.read()["au"]["governance"]["valid_until"]
        with patch("ai_union.application.governance.time.time", return_value=deadline + 1):
            self.assertEqual(self.read()["governance_status"], "exited")
            self.reject("renew_governance", {"reason": "Expired means stopped"})
            self.success("exit_governance", {"reason": "Record already effective timeout exit"})
            self.reject("configure_governance", {"config": self.config(), "reason": "Cannot resurrect exited governance"})
        after = self.read()["au"]
        self.assertEqual(after["governance_root"], before["governance_root"])
        self.assertEqual(after["governance"]["status"], "exited")

    def test_failed_amendment_is_atomic_and_original_id_recovers_one_adoption(self):
        self.prepare()
        self.activate()
        before = self.dump()
        with closing(sqlite3.connect(self.database())) as cx, cx:
            cx.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON governance_events BEGIN SELECT RAISE(ABORT, 'controlled audit failure'); END")
        with_trigger = self.dump()
        status, result, request = self.command("amend_charter", {"charter": self.read()["au"]["charter"], "reason": "Atomic revision"})
        self.assertEqual((status, result.get("code")), (503, "storage_unavailable"), result)
        self.assertEqual(self.dump(), with_trigger)
        with closing(sqlite3.connect(self.database())) as cx, cx:
            cx.execute("DROP TRIGGER fail_audit")
        self.assertEqual(self.dump(), before)
        status, value, _ = self.request("/api/v1/governance/commands", request)
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], "succeeded")
        after = self.dump()
        self.assertEqual(self.request("/api/v1/governance/commands", request)[1]["receipt"], receipt)
        self.assertEqual(self.dump(), after)
        self.assertEqual(self.read()["au"]["charter_version"], 2)

    def test_activation_revalidates_the_preconfirmed_successor_account(self):
        owner = (self.token, self.app.session(self.token)["principal_id"])
        creator = self.participant("core-creator")
        self.token = creator[0]
        self.prepare()
        self.success("adopt_governance", {"config": self.config(owner[1]), "reason": "Choose a known recovery subject"})
        self.success("acknowledge_recovery", {"reason": "Confirm recovery role"}, token=owner[0])
        self.stop()
        from scripts.reset_owner import reset
        reset(self.root, confirm=True)
        self.start()
        self.reject("activate_governance", {"reason": "Former confirmation cannot substitute for a current identity"})
        self.assertEqual(self.read()["governance_status"], "prepared")
        self.success("configure_governance", {"config": self.config(), "reason": "Explicitly adopt supported timeout exit"})
        self.success("activate_governance", {"reason": "Current configuration is usable"})

    def test_lost_successor_identity_blocks_actions_until_current_governor_reconfigures(self):
        owner = (self.token, self.app.session(self.token)["principal_id"])
        creator = self.participant("core-creator")
        self.token = creator[0]
        self.prepare(); self.activate(owner)
        self.appoint(); self.work(); self.grant()
        self.stop()
        from scripts.reset_owner import reset
        reset(self.root, confirm=True)
        self.start()
        self.assertFalse(self.read()["capabilities"]["local_submission"])
        self.reject("begin_local_action", {"attempt_id": "no-recovery", "work_id": "work-a", "mandate_id": "mandate-a"})
        self.reject("renew_governance", {"reason": "Cannot renew an unavailable recovery program"})
        self.success("configure_governance", {"config": self.config(), "reason": "Adopt a usable program under current authority"})
        self.success("activate_governance", {"reason": "Ready again"})
