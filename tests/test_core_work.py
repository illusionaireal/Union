"""S03.1: one goal becomes an answerable AI work under effective local governance."""
import copy
import uuid

from tests.model_access_support import ModelAccessCase
from tests.test_core_creation import creation


def work_data(**changes):
    data = {"work_id": "work-overview", "title": "项目概览", "member_name": "资料整理 Agent",
            "goal": "阅读我授权的资料目录，写一份带文件引用的项目概览",
            "member_id": "member-ai-overview", "binding_id": "binding-ai-overview",
            "mandate_id": "mandate-ai-overview", "definition_id": "definition-ai-overview",
            "connection_id": "connection-a", "expected_revision": 1,
            "materials_root": "project-docs", "max_calls": 4, "tools": ["read_document"],
            "reason": "用户要求以授权资料形成第一份可阅读成果"}
    data.update(changes)
    return data


class CoreWorkTests(ModelAccessCase):
    def adopt_default(self):
        return self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": 1,
                                                     "enabled": True, "make_default": True})

    def work_command(self, au_id, kind, data, *, token="current", version=None, request_id=None):
        if version is None:
            version = self.request("/api/v1/aus/" + au_id, token=token)[1]["au"]["version"]
        request = {"id": request_id or str(uuid.uuid4()), "organization_id": au_id,
                   "base_version": version, "kind": kind, "data": copy.deepcopy(data)}
        status, value, _ = self.request("/api/v1/work/commands", request, token)
        return status, value, request

    def work(self, au_id=None, data=None, **kwargs):
        return self.work_command(au_id or self.au_id, "start_work", data or work_data(), **kwargs)

    def works(self, au_id=None, token="current"):
        status, value, _ = self.request("/api/v1/work?organization_id=" + (au_id or self.au_id), token=token)
        self.assertEqual(status, 200, value)
        return value

    def second_au(self, request_id="v1-create-second"):
        receipt = self.create(creation(request_id))
        return receipt["organization_id"]

    def test_start_work_binds_ai_member_definition_binding_work_and_mandate_in_one_command(self):
        self.saved()
        default = self.adopt_default()[0]
        before = self.read()["au"]["version"]
        status, value, request = self.work()
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], "rejected", receipt)
        self.assertIn("章程", receipt["message"])
        self.assertEqual(self.read()["au"]["version"], before)

        self.allow_documents()
        before = self.read()["au"]["version"]
        status, value, request = self.work()
        self.assertEqual(status, 200, value)
        receipt = value["receipt"]
        self.assertEqual(receipt["status"], "succeeded", receipt)
        self.assertEqual(receipt["work_id"], "work-overview")
        self.assertEqual(receipt["version"], before + 1)
        self.assertEqual(self.read()["au"]["version"], before + 1)

        card = self.works()
        self.assertEqual(card["protocol"], "core.work.v1")
        self.assertTrue(card["access"]["can_start"])
        self.assertEqual(len(card["works"]), 1)
        work = card["works"][0]
        self.assertEqual((work["id"], work["status"], work["max_calls"], work["materials_root"]),
                         ("work-overview", "pending", 4, "project-docs"))
        self.assertEqual(work["responsible"], {"member_id": "member-ai-overview", "name": "资料整理 Agent",
                                              "binding_id": "binding-ai-overview", "duty": "项目概览"})
        self.assertEqual(work["definition"], {"id": "definition-ai-overview", "version": 1,
                                              "connection_id": "connection-a", "model": "model-a",
                                              "tools": ["read_document"]})
        self.assertEqual(work["mandate"], {"id": "mandate-ai-overview", "version": 1, "actions": ["read_document"], "active": True})
        self.assertEqual(card["capabilities"]["execution"], "not_started")

        replay_status, replay, _ = self.request("/api/v1/work/commands", request)
        self.assertEqual(replay_status, 200, replay)
        self.assertEqual(replay["receipt"], receipt)
        self.assertEqual(len(self.works()["works"]), 1)
        self.assertEqual(self.read()["au"]["version"], before + 1)
        connection = next(item for item in self.models()["connections"] if item["id"] == "connection-a")
        self.assertTrue(connection["is_default"])

        state = self.read()["au"]
        self.assertNotIn("/", str(state.get("work_runtime", {}).get("works", {})), "host paths never enter AU state")

    def test_start_work_requires_effective_governance_and_the_current_governor(self):
        self.saved()
        self.adopt_default()
        self.allow_documents()
        token, _ = self.participant("outsider")
        status, value, _ = self.work(token=token, version=self.read()["au"]["version"])
        self.assertEqual(status, 403, value)
        self.assertEqual(value.get("code"), "not_authorized")

        other = self.second_au()
        before = self.request("/api/v1/aus/" + other)[1]["au"]["version"]
        status, value, _ = self.work(au_id=other)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("治理", value["receipt"]["message"])
        self.assertEqual(value["receipt"]["version"], before)
        self.assertEqual(self.request("/api/v1/aus/" + other)[1]["au"]["version"], before)
        self.assertEqual(self.works(au_id=other)["works"], [])

    def test_start_work_refuses_unadopted_model_unbounded_calls_paths_and_duplicate_ids(self):
        unknown = self.work(au_id=self.second_au())
        self.assertEqual(unknown[1]["receipt"]["status"], "rejected", unknown[1])

        self.saved()
        self.adopt_default()
        self.allow_documents()
        status, value, _ = self.work(data=work_data(max_calls=13))
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("剩余", value["receipt"]["message"])

        for materials_root in ("/etc/passwd", "C:\\docs", "..\\secrets", "a/b"):
            status, value, _ = self.work(data=work_data(materials_root=materials_root))
            self.assertEqual(value["receipt"]["status"], "rejected", value)
            self.assertIn("资料目录", value["receipt"]["message"])

        status, value, _ = self.work(data=work_data(tools=["workspace_execute"]))
        self.assertEqual(value["receipt"]["status"], "rejected", value)
        self.assertIn("工具", value["receipt"]["message"])

        status, value, _ = self.work(data=work_data(connection_id="connection-missing"))
        self.assertEqual(value["receipt"]["status"], "rejected", value)

        status, succeeded, _ = self.work()
        self.assertEqual(status, 200, succeeded)
        self.assertEqual(succeeded["receipt"]["status"], "succeeded", succeeded)
        status, duplicate, _ = self.work()
        self.assertEqual(duplicate["receipt"]["status"], "rejected", duplicate)
        self.assertIn("已存在", duplicate["receipt"]["message"])
        self.assertEqual(len(self.works()["works"]), 1)
