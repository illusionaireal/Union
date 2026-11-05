"""Actual local work respects current authority at action, submission and adoption."""
import copy
import hashlib
from unittest.mock import patch

from tests.governance_support import GovernanceCase
from tests.test_core_creation import creation


class ResponsibilityTests(GovernanceCase):
    def setUp(self):
        super().setUp()
        self.prepare()
        self.activate()
        self.appoint()
        self.work()
        self.grant(delegate=True)

    def begin(self, attempt="attempt-a", mandate="mandate-a", token="current", **extra):
        return self.success("begin_local_action", {"attempt_id": attempt, "work_id": "work-a", "mandate_id": mandate}, token=token, **extra)

    def submit(self, content="Observed and checked internal facts", attempt="attempt-a", token="current"):
        return self.success("submit_local_result", {"attempt_id": attempt, "content": content}, token=token)

    def test_authorized_local_work_persists_a_checked_result_without_external_execution(self):
        self.begin()
        attempt = self.read()["au"]["attempts"]["attempt-a"]
        self.assertEqual((attempt["kind"], attempt["member_id"], attempt["principal_id"]), ("local_submission", "member-a", self.principal))
        self.assertEqual(attempt["mandates"], [{"id": "mandate-a", "version": 1}])
        self.submit()
        self.assertEqual(self.read()["au"]["work"]["work-a"]["status"], "open")
        self.success("accept_local_result", {"attempt_id": "attempt-a", "reason": "Check the internal evidence"})
        value = self.read()["au"]
        result = next(iter(value["results"].values()))
        self.assertEqual(result["content"], "Observed and checked internal facts")
        self.assertEqual(result["sha256"], hashlib.sha256(result["content"].encode()).hexdigest())
        self.assertEqual(result["author_member_id"], "member-a")
        self.assertEqual(value["work"]["work-a"]["status"], "delivered")
        self.assertEqual(value["work"]["work-a"]["result_ids"], [result["id"]])
        self.assertEqual(self.app.jobs, [])
        self.stop(); self.start()
        self.assertEqual(self.read()["au"], value)

    def test_revocation_blocks_new_action_and_retains_late_content_only_as_unadopted_evidence(self):
        self.begin()
        self.success("revoke_mandate", {"mandate_id": "mandate-a", "reason": "Revoke this authority"})
        self.reject("begin_local_action", {"attempt_id": "attempt-new", "work_id": "work-a", "mandate_id": "mandate-a"})
        receipt, _ = self.reject("submit_local_result", {"attempt_id": "attempt-a", "content": "Late factual output"})
        value = self.read()["au"]
        self.assertEqual(value["attempts"]["attempt-a"]["status"], "not_adopted")
        self.assertEqual(value["attempts"]["attempt-a"]["content"], "Late factual output")
        self.assertEqual(receipt["effect"], "evidence_only")
        self.reject("accept_local_result", {"attempt_id": "attempt-a", "reason": "Do not grant authority retroactively"})
        self.assertEqual(self.read()["au"]["results"], {})
        self.assertEqual(self.read()["au"]["work"]["work-a"]["status"], "open")

    def test_result_acceptance_rechecks_authority_after_a_valid_submission(self):
        self.begin(); self.submit()
        self.success("revoke_mandate", {"mandate_id": "mandate-a", "reason": "Revoked before acceptance"})
        self.reject("accept_local_result", {"attempt_id": "attempt-a", "reason": "Current authority must be rechecked"})
        self.assertEqual(self.read()["au"]["results"], {})
        self.assertEqual(self.read()["au"]["attempts"]["attempt-a"]["status"], "submitted")

    def test_changed_goal_invalidates_old_actions_and_result_acceptance(self):
        self.begin(); self.submit()
        self.success("set_goal", {"goal": "A newly authorized objective", "reason": "Goal changes scope"})
        self.reject("begin_local_action", {"attempt_id": "stale-goal", "work_id": "work-a", "mandate_id": "mandate-a"})
        self.reject("accept_local_result", {"attempt_id": "attempt-a", "reason": "Old objective does not authorize acceptance"})

    def test_changed_appointment_duty_invalidates_old_authority(self):
        self.begin(); self.submit()
        self.success("update_appointment", {"binding_id": "binding-a", "duty": "A different responsibility", "reason": "Change scope"})
        self.reject("begin_local_action", {"attempt_id": "stale-role", "work_id": "work-a", "mandate_id": "mandate-a"})
        self.reject("accept_local_result", {"attempt_id": "attempt-a", "reason": "Original duty no longer applies"})

    def test_work_scope_and_stop_changes_invalidate_pending_attempts(self):
        self.begin(); self.submit()
        self.success("update_work", {"work_id": "work-a", "title": "Stopped record", "instruction": "Changed instruction",
                                     "status": "stopped", "reason": "Stop and revise this work"})
        self.reject("begin_local_action", {"attempt_id": "stopped", "work_id": "work-a", "mandate_id": "mandate-a"})
        self.reject("accept_local_result", {"attempt_id": "attempt-a", "reason": "A stopped work cannot accept results"})
        self.success("update_work", {"work_id": "work-a", "title": "Resume reviewed scope", "instruction": "Changed instruction",
                                     "status": "open", "reason": "Explicitly resume new version"})
        self.reject("begin_local_action", {"attempt_id": "old-scope", "work_id": "work-a", "mandate_id": "mandate-a"})
        self.grant("fresh-scope")
        self.begin("fresh-attempt", "fresh-scope")

    def test_charter_revocation_changes_the_same_local_action_and_acceptance_path(self):
        self.begin(); self.submit()
        charter = copy.deepcopy(self.read()["au"]["charter"])
        charter["allowed_operations"].remove("record_memory")
        self.success("amend_charter", {"charter": charter, "reason": "Revoke the supported local operation"})
        self.reject("begin_local_action", {"attempt_id": "forbidden-op", "work_id": "work-a", "mandate_id": "mandate-a"})
        self.reject("accept_local_result", {"attempt_id": "attempt-a", "reason": "Old permissions are insufficient"})

    def test_expired_governance_rejects_old_result_and_new_action(self):
        self.begin(); self.submit()
        deadline = self.read()["au"]["governance"]["valid_until"]
        with patch("ai_union.application.governance.time.time", return_value=deadline + 1):
            self.reject("begin_local_action", {"attempt_id": "expired", "work_id": "work-a", "mandate_id": "mandate-a"})
            self.reject("accept_local_result", {"attempt_id": "attempt-a", "reason": "Expired governing term"})
            self.success("exit_governance", {"reason": "Close the expired governing program"})
        value = self.read()["au"]
        self.assertEqual(value["work"]["work-a"]["responsible_binding_id"], "binding-a")
        self.assertEqual(value["attempts"]["attempt-a"]["status"], "submitted")
        self.assertEqual(value["results"], {})

    def test_finite_redelegation_revokes_through_ancestors_without_stopping_unrelated_work(self):
        second = self.participant("second")
        third = self.participant("third")
        self.appoint("member-b", "binding-b", second[1])
        self.appoint("member-c", "binding-c", third[1])
        self.grant("mandate-b", binding="binding-b", parent="mandate-a", delegate=True)
        self.grant("mandate-c", binding="binding-c", parent="mandate-b", token=second[0])
        self.begin("delegated", "mandate-c", third[0])
        self.submit(attempt="delegated", token=third[0])
        self.work("independent")
        self.grant("independent-authority", "independent")
        self.success("revoke_mandate", {"mandate_id": "mandate-a", "reason": "Revoke ancestor authority"})
        self.reject("begin_local_action", {"attempt_id": "new-delegated", "work_id": "work-a", "mandate_id": "mandate-c"}, token=third[0])
        self.reject("accept_local_result", {"attempt_id": "delegated", "reason": "Ancestor no longer valid"})
        self.success("begin_local_action", {"attempt_id": "unrelated", "work_id": "independent", "mandate_id": "independent-authority"})

    def test_redelegation_cannot_expand_actions_work_or_permission_to_delegate(self):
        second = self.participant("second")
        self.appoint("member-b", "binding-b", second[1])
        self.grant("child", binding="binding-b", parent="mandate-a")
        data = {"mandate_id": "too-far", "work_id": "work-a", "binding_id": "binding-a", "parent_id": "child",
                "actions": ["record_memory"], "can_delegate": False}
        self.reject("grant_mandate", data, token=second[0])
        data["actions"] = ["workspace_execute"]
        self.assertEqual(self.command("grant_mandate", data, token=second[0])[0], 400)
        self.work("other-work")
        data.update(actions=["record_memory"], parent_id="mandate-a", work_id="other-work")
        self.reject("grant_mandate", data)

    def test_handoff_preserves_original_work_history_and_delivered_ownership(self):
        self.begin(); self.submit()
        self.success("accept_local_result", {"attempt_id": "attempt-a", "reason": "Complete original record"})
        completed = copy.deepcopy(self.read()["au"]["work"]["work-a"])
        result = copy.deepcopy(self.read()["au"]["results"])
        self.work("unfinished")
        self.grant("unfinished-auth", "unfinished")
        self.success("begin_local_action", {"attempt_id": "unfinished-attempt", "work_id": "unfinished", "mandate_id": "unfinished-auth"})
        successor = self.participant("successor")
        self.appoint("member-b", "binding-b", successor[1])
        self.success("handoff_responsibility", {"from_binding_id": "binding-a", "to_binding_id": "binding-b", "reason": "Hand over the checked materials and outstanding obligation"})
        state = self.read()["au"]
        self.assertFalse(state["bindings"]["binding-a"]["active"])
        self.assertEqual(state["work"]["work-a"], completed)
        self.assertEqual(state["results"], result)
        self.assertEqual(state["work"]["unfinished"]["responsible_binding_id"], "binding-b")
        self.assertTrue(state["work"]["unfinished"]["history"])
        self.assertIn("unfinished-attempt", state["attempts"])
        self.reject("submit_local_result", {"attempt_id": "unfinished-attempt", "content": "Late output from old assignment"})
        self.success("update_work", {"work_id": "unfinished", "title": "Continue same Work", "instruction": "Review handover and continue",
                                    "status": "open", "reason": "New responsible member reviewed old attempt"})
        self.grant("successor-auth", "unfinished", "binding-b")
        self.success("begin_local_action", {"attempt_id": "successor-attempt", "work_id": "unfinished", "mandate_id": "successor-auth"}, token=successor[0])
        self.success("submit_local_result", {"attempt_id": "successor-attempt", "content": "Continued from the original obligation"}, token=successor[0])
        self.success("accept_local_result", {"attempt_id": "successor-attempt", "reason": "Accept continuation of original work"})
        self.assertEqual(self.read()["au"]["work"]["unfinished"]["status"], "delivered")

    def test_other_account_or_au_cannot_reuse_a_scoped_mandate_or_attempt(self):
        self.begin()
        other = self.participant("other")
        version = self.read()["au"]["version"]
        self.assertEqual(self.command("submit_local_result", {"attempt_id": "attempt-a", "content": "Impersonated"}, token=other[0], version=version)[0], 403)
        self.au_id = self.create(creation("separate-au"))["organization_id"]
        self.activate()
        self.reject("begin_local_action", {"attempt_id": "cross-au", "work_id": "work-a", "mandate_id": "mandate-a"})
        self.assertEqual(self.read()["au"]["attempts"], {})

    def test_governance_nomination_does_not_replace_an_independent_member_mandate(self):
        member = self.participant("nominee")
        self.appoint("member-b", "binding-b", member[1])
        self.grant("member-authority", binding="binding-b")
        self.begin("before-nomination", "member-authority", member[0])
        self.success("nominate_governor", {"principal_id": member[1], "reason": "A distinct governing role"})
        self.begin("after-nomination", "member-authority", member[0])
        self.assertIn("begin_local_action", self.read(member[0])["access"]["commands"])

    def test_successor_member_and_nominee_rights_compose_without_shadowing(self):
        member = self.participant("successor-member")
        self.appoint("member-b", "binding-b", member[1])
        self.success("configure_governance", {"config": self.config(member[1]), "reason": "Independent recovery duty"})
        self.success("acknowledge_recovery", {"reason": "Confirm recovery"}, token=member[0])
        self.success("activate_governance", {"reason": "Confirmed term"})
        self.grant("member-authority", binding="binding-b")
        self.begin("successor-member-attempt", "member-authority", member[0])
        self.success("nominate_governor", {"principal_id": member[1], "reason": "Also nominate for ordinary handoff"})
        deadline = self.read()["au"]["governance"]["valid_until"]
        with patch("ai_union.application.governance.time.time", return_value=deadline + 1):
            self.assertIn("recover_governance", self.read(member[0])["access"]["commands"])
            self.success("recover_governance", {"reason": "Use preaccepted expiry recovery"}, token=member[0])

    def test_handoff_of_outstanding_responsibility_does_not_require_the_lost_subject_account(self):
        successor = self.participant("new-governor")
        self.success("nominate_governor", {"principal_id": successor[1], "reason": "Transfer governance before losing credentials"})
        self.success("accept_governance", {"reason": "Accept current governing duty"}, token=successor[0])
        self.stop()
        from scripts.reset_owner import reset
        reset(self.root, confirm=True)
        self.start()
        self.token, self.principal = successor
        self.success("configure_governance", {"config": self.config(), "reason": "Adopt successor term"})
        self.success("activate_governance", {"reason": "Continue local governance"})
        self.appoint("member-b", "binding-b", successor[1])
        self.success("handoff_responsibility", {"from_binding_id": "binding-a", "to_binding_id": "binding-b", "reason": "Old subject is unavailable; retain and transfer their original responsibility"})
        self.assertEqual(self.read()["au"]["work"]["work-a"]["responsible_binding_id"], "binding-b")
