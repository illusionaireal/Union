"""Real SDK with HTTP and container doubles. No real model/container claim."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_union.executor import ExecutionFailure
from ai_union.harness import HarnessExecutor
from ai_union.model_api import resolve_connection
from ai_union.runner import run
from ai_union import workspace
from tests import test_harness
from tests.test_agent_conversation import PLAN, tool


class WorkspaceHarnessTests(unittest.TestCase):
    setUp = test_harness.HarnessTests.setUp
    command = test_harness.HarnessTests.command
    configure = test_harness.HarnessTests.configure
    bind = test_harness.HarnessTests.bind
    replies = test_harness.HarnessTests.replies
    batch = test_harness.HarnessTests.batch
    executor = test_harness.HarnessTests.executor

    def ready(self):
        charter = self.e.charter()
        charter["allowed_tools"].append(workspace.TOOL)
        key = (self.e.root / "board.key").read_text()
        self.e.amend(key, charter, "test workspace")
        directory = Path(self.temp.name) / "checkout"
        directory.mkdir()
        workspace.configure(self.e, key, {"directory": str(directory), "image": "sha256:" + "a" * 64,
                                        "timeout_seconds": 30, "enabled": True}, "test host grant")
        plan = copy.deepcopy(PLAN)
        for member in plan["members"]:
            member["tools"] = [workspace.TOOL]
        executor = self.executor()
        self.replies(tool("initialize_organization", plan))
        self.assertEqual(run(self.e, executor, 1)[0]["action"], "decision")
        return executor, directory

    def test_tool_results_and_files_pass_between_members_with_real_checkpoints(self):
        executor, directory = self.ready()
        self.replies(tool(workspace.TOOL, {"command": "write change"}),
                     {"role": "assistant", "content": "已实现修改，详见命令回执。"},
                     tool(workspace.TOOL, {"command": "read and test"}),
                     {"role": "assistant", "content": "已读取前一成员的修改并验证。"})

        def sandbox(config, command, name):
            target = Path(config["directory"]) / "change.txt"
            if command == "write change":
                target.write_text("shared change")
                return {"exit_code": 0, "output": "written by sandbox double"}
            return {"exit_code": 0, "output": target.read_text() + "; tests passed (double)"}

        with patch.object(workspace, "run_container", side_effect=sandbox) as sandbox:
            first = run(self.e, executor, 1)
            second = run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 3)
        self.assertEqual([a["action"] for a in first + second], ["progress", "work", "progress", "work"])
        self.assertEqual(sandbox.call_count, 2)
        self.assertEqual(len(self.e.state()["artifacts"]), 2)
        self.assertIn("shared change", json.dumps(self.provider.requests[-1]["body"]))
        self.assertEqual(len(workspace.receipts(self.e)), 2)
        self.assertEqual(self.e.status()["budget"]["calls_reserved"], 5)

    def test_unknown_sandbox_propagates_through_sdk_and_blocks_fresh_executor(self):
        executor, _ = self.ready()
        self.replies(tool(workspace.TOOL, {"command": "change"}))
        with patch.object(workspace, "run_container", side_effect=ExecutionFailure("timeout", unknown=True)) as sandbox:
            actions = run(self.e, executor, 1)
            again = run(self.e, HarnessExecutor(self.e, resolve_connection(self.e)), 1)
        self.assertEqual(actions[-1]["action"], "blocked", actions)
        self.assertEqual(again[-1]["action"], "blocked", again)
        self.assertEqual(self.e.runs()[-1]["status"], "unknown")
        self.assertEqual(self.e.runs()[-1]["usage"]["output_tokens"], 10)
        self.assertEqual(sandbox.call_count, 1)

    def test_mixed_commands_do_not_execute_partially(self):
        executor, _ = self.ready()
        self.replies(self.batch((workspace.TOOL, {"command": "one"}), (workspace.TOOL, {"command": "two"})))
        with patch.object(workspace, "run_container") as sandbox:
            run(self.e, executor, 1)
        sandbox.assert_not_called()
        self.assertEqual(workspace.receipts(self.e), [])

    def test_bootstrap_cannot_assign_tools_outside_charter(self):
        executor = self.executor()
        member = PLAN["members"][0] | {"tools": [workspace.TOOL]}
        self.replies(tool("prepare_member", member))
        run(self.e, executor, 1)
        self.assertEqual(self.e.state()["members"], {})
        self.assertFalse(self.e.status()["bootstrap"] and self.e.status()["bootstrap"]["members"])


if __name__ == "__main__":
    unittest.main()
