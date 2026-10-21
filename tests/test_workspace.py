"""Deterministic host/sandbox doubles; these do not prove container isolation."""
import copy
import tempfile
import unittest
import sys
import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from ai_union.engine import Rejected
from ai_union.executor import ExecutionFailure
from ai_union import workspace
from tests.support import init, organization, decision


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.e = init(Path(self.temp.name) / "org")
        self.directory = Path(self.temp.name) / "checkout"
        self.directory.mkdir()
        self.config = {"directory": str(self.directory), "image": "sha256:" + "a" * 64,
                       "timeout_seconds": 30, "enabled": True}
        self.charter = self.e.charter()
        self.charter["allowed_tools"].append("workspace_execute")
        self.e.amend("test-key", self.charter, "test grant")
        organization(self.e)
        self.e.apply_decision(decision(self.e, [{"op": "update_position", "position_id": "p1",
            "title": "Engineering", "mandate": "Develop in the bound workspace",
            "permissions": self.e.state()["positions"]["p1"]["permissions"] + ["workspace_execute"]}]), "m1", "a1")
        workspace.configure(self.e, "test-key", self.config, "test host binding")
        self.package = self.e.begin_work("w1", "fixture")

    def execute(self, command="python -m unittest"):
        return workspace.execute(self.e, self.package, command)

    def test_command_receipt_is_idempotent_and_survives_reopen(self):
        from ai_union.engine import Engine
        with patch.object(workspace, "run_container", return_value={"exit_code": 0, "output": "tests passed"}) as sandbox:
            first = self.execute()
            self.e = Engine(self.e.root)
            self.assertEqual(self.execute(), first)
            self.assertEqual(sandbox.call_count, 1)
            with self.assertRaises(Rejected):
                self.execute("different command")
        self.assertEqual(first["exit_code"], 0)
        self.assertEqual(workspace.receipts(self.e)[0]["status"], "completed")

    def test_current_authority_and_pause_rechecked_before_sandbox(self):
        cases = ("pause", "position", "assignment", "charter", "work_version")
        for case in cases:
            with self.subTest(case=case), self.e.transaction() as cx:
                original = self.e._state(cx)
                state = copy.deepcopy(original)
                if case == "pause":
                    self.e.set_paused(True)
                elif case == "position":
                    state["positions"]["p1"]["permissions"].remove("workspace_execute")
                elif case == "assignment":
                    state["assignments"]["a1"]["active"] = False
                elif case == "charter":
                    state["charter_version"] += 1
                else:
                    state["work"]["w1"]["version"] += 1
                self.e._save(cx, state)
                with patch.object(workspace, "run_container") as sandbox, self.assertRaises(Rejected):
                    self.execute()
                sandbox.assert_not_called()
                self.e._save(cx, original)
                self.e.set_paused(False)

    def test_missing_runtime_never_falls_back_to_host_shell(self):
        with patch.object(workspace.shutil, "which", return_value=None), self.assertRaises(Rejected):
            self.execute()
        self.assertEqual(workspace.receipts(self.e)[0]["status"], "failed_before_start")

    def test_unknown_command_is_never_replayed_or_erased_by_reconfiguration(self):
        with patch.object(workspace, "run_container", side_effect=ExecutionFailure("timeout", unknown=True)) as sandbox:
            with self.assertRaises(ExecutionFailure):
                self.execute()
            with self.assertRaises(ExecutionFailure):
                self.execute()
            self.assertEqual(sandbox.call_count, 1)
        self.assertEqual(workspace.receipts(self.e)[0]["status"], "unknown")
        with self.assertRaises(Rejected):
            workspace.configure(self.e, "test-key", self.config, "must not reset")

    def test_crash_receipt_blocks_later_command_until_explicit_reconciliation(self):
        with patch.object(workspace, "run_container", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.execute()
        with self.assertRaises(Rejected):
            workspace.reconcile(self.e, "test-key", self.package["run_id"], "not yet reconciled run")
        self.e.fail_run(self.package["run_id"], "interrupted", unknown=True)
        self.e.reconcile("test-key", self.package["run_id"], "abandon", "test confirmed container stopped")
        workspace.reconcile(self.e, "test-key", self.package["run_id"], "test inspected retained files and stopped container")
        self.assertEqual(workspace.receipts(self.e)[0]["status"], "reconciled")

    def test_adapter_error_remains_unknown_and_can_be_reconciled(self):
        with patch.object(workspace, "run_container", side_effect=OSError("adapter cleanup failure")):
            with self.assertRaises(ExecutionFailure) as caught:
                self.execute()
        self.assertTrue(caught.exception.unknown)
        self.assertEqual(workspace.receipts(self.e)[0]["status"], "unknown")

    def test_disable_retains_unknown_receipts_even_when_directory_disappears(self):
        with patch.object(workspace, "run_container", side_effect=ExecutionFailure("unknown", unknown=True)), self.assertRaises(ExecutionFailure):
            self.execute()
        self.directory.rmdir()
        result = workspace.disable(self.e, "test-key", "test emergency revoke")
        self.assertFalse(result["enabled"])
        self.assertFalse(workspace.binding(self.e)["config"]["enabled"])
        self.assertEqual(workspace.receipts(self.e)[0]["status"], "unknown")

    def test_failure_receipt_write_error_does_not_lose_unknown_classification(self):
        transaction = self.e.transaction
        count = 0

        @contextmanager
        def failing_transaction():
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("storage unavailable after command")
            with transaction() as cx:
                yield cx

        with patch.object(self.e, "transaction", failing_transaction), patch.object(workspace, "run_container", side_effect=ExecutionFailure("timeout", unknown=True)):
            with self.assertRaises(ExecutionFailure) as caught:
                self.execute()
        self.assertTrue(caught.exception.unknown)
        self.assertEqual(workspace.receipts(self.e)[0]["status"], "started")

    def test_host_binding_rejects_board_failure_and_private_directory_overlap(self):
        with self.assertRaises(Rejected):
            workspace.configure(self.e, "wrong-key", self.config, "test")
        for directory in (self.e.root, self.e.root.parent, self.e.root / "assets"):
            with self.subTest(directory=directory), self.assertRaises(Rejected):
                workspace.validate_config(self.e, self.config | {"directory": str(directory)})
        (self.directory / "linked").symlink_to(self.e.root, target_is_directory=True)
        with self.assertRaises(Rejected):
            workspace.validate_config(self.e, self.config)

    @unittest.skipUnless(sys.platform == "linux", "Linux-only container host")
    def test_container_command_exposes_only_selected_workspace_without_network_or_secrets(self):
        argv = workspace.container_argv(self.config, "printf hello", "union-test", "/tmp/docker-config")
        self.assertIn("--network=none", argv)
        self.assertIn("--read-only", argv)
        self.assertIn("--pull=never", argv)
        self.assertIn("--cap-drop=ALL", argv)
        self.assertEqual(argv.count("--mount"), 1)
        self.assertIn("dst=/workspace", argv[argv.index("--mount") + 1])
        self.assertNotIn(str(self.e.root), " ".join(argv))
        self.assertEqual(argv[-3:], [self.config["image"], "-c", "printf hello"])

    @unittest.skipUnless(sys.platform == "linux", "Linux-only container host")
    def test_attach_client_exit_requires_container_stop_evidence(self):
        # Local children simulate only the CLI process; no container is launched.
        for state in ({"Running": True, "Status": "running", "ExitCode": 0},
                      {"Running": False, "Status": "exited", "ExitCode": 7}):
            process = subprocess.Popen([sys.executable, "-c", "print('cli-double')"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            inspected = subprocess.CompletedProcess([], 0, json.dumps(state).encode())
            with patch.object(workspace.shutil, "which", return_value="/usr/bin/docker"), patch.object(workspace.subprocess, "Popen", return_value=process), patch.object(workspace.subprocess, "run", return_value=inspected):
                if state["Running"]:
                    with self.assertRaises(ExecutionFailure) as caught:
                        workspace.run_container(self.config, "unused", "union-double")
                    self.assertTrue(caught.exception.unknown)
                else:
                    result = workspace.run_container(self.config, "unused", "union-double")
                    self.assertEqual(result["exit_code"], 7)
                    self.assertTrue(result["container_exit_confirmed"])

    @unittest.skipUnless(sys.platform == "linux", "Linux-only container host")
    def test_killed_attach_client_is_unknown(self):
        process = subprocess.Popen([sys.executable, "-c", "import os,signal; os.kill(os.getpid(), signal.SIGKILL)"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with patch.object(workspace.shutil, "which", return_value="/usr/bin/docker"), patch.object(workspace.subprocess, "Popen", return_value=process), patch.object(workspace.subprocess, "run"):
            with self.assertRaises(ExecutionFailure) as caught:
                workspace.run_container(self.config, "unused", "union-double")
        self.assertTrue(caught.exception.unknown)


if __name__ == "__main__":
    unittest.main()
