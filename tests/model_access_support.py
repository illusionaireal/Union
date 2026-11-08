"""S02 HTTP fixtures; the model double is explicit, not real-profile evidence."""
import copy
import json
import time
import uuid
from unittest.mock import patch

from ai_union.model_service import ServiceError
from tests.governance_support import GovernanceCase


class ModeldDouble:
    def __init__(self):
        self.au_id = None
        self.registrations = {}
        self.requests = {}
        self.posts = []
        self.grant_revision = 1
        self.revoked = False
        self.lost_save = False
        self.lost_submit = False
        self.before_result = None
        self.result_state = "completed"

    def runtime(self):
        return {"protocol_version": 1, "profiles": ["openai_compatible", "opencode-go"]}

    def call(self, method, path, body=None, **kwargs):
        if method == "POST" and path == "/v1/api-connections":
            self.posts.append((path, copy.deepcopy(body)))
            self.registrations[body["id"]] = {k: body[k] for k in ("id", "au_id", "principal_id", "name", "model_id")}
            self.registrations[body["id"]].update(profile="openai_compatible", grant_ref="grant-a", grant_revision=1)
            if self.lost_save:
                raise ServiceError("lost_acceptance")
            return copy.deepcopy(self.registrations[body["id"]])
        if method == "GET" and path.startswith("/v1/api-connections/"):
            key = path.split("/v1/api-connections/")[1].split("?")[0]
            if key not in self.registrations:
                raise ServiceError("not_found", 404)
            return copy.deepcopy(self.registrations[key])
        if path.startswith("/v1/grants/"):
            return {"id": "grant-a", "au_id": self.au_id, "account_ref": "account-a", "model_ids": ["model-a"],
                    "revision": self.grant_revision, "revoked_at": "revoked" if self.revoked else None}
        if method == "POST" and path == "/v1/requests":
            self.posts.append((path, copy.deepcopy(body)))
            assert body["id"] not in self.requests, "A model attempt was dispatched twice"
            self.requests[body["id"]] = copy.deepcopy(body)
            if self.lost_submit:
                raise ServiceError("lost_acceptance")
            return {"id": body["id"], "au_id": body["au_id"], "state": "queued"}
        if path.endswith("/cancel") or "/cancel?" in path:
            return {}
        raise AssertionError((method, path))

    def request(self, request_id, au_id):
        import hashlib
        body = self.requests.get(request_id)
        if body is None:
            raise ServiceError("not_found", 404)
        if self.before_result:
            callback, self.before_result = self.before_result, None
            callback()
        if body["tools"]:
            props = body["tools"][0]["function"]["parameters"]["properties"]
            document_id = props["document_id"]["enum"][0]
            message = {"role": "assistant", "content": "", "tool_calls": [{"id": "call-document", "type": "function",
                "function": {"name": "read_document", "arguments": json.dumps({"document_id": document_id})}}]}
        else:
            result = json.loads(body["messages"][-1]["content"])
            message = {"role": "assistant", "content": "资料概要：" + result["content"][:80] + "；校验码：" + result["challenge"]}
        message["_native"] = {"au_id": au_id, "account_ref": "account-a", "model_id": "model-a", "upstream": "test-native",
                              "message": {"role": "assistant", "content": [{"type": "text", "text": message["content"]}]}}
        return {"id": request_id, "au_id": au_id, "state": self.result_state, "action_authorized": not self.revoked,
                "request_digest": hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "result": {"message": message, "usage": {"input_tokens": 25, "output_tokens": 12,
                    "account_ref": "account-a", "resolved_model": "model-a", "modeld_usage": {"inputTokens": 25, "outputTokens": 12}}}}

    def events(self, request_id, au_id, after=0):
        return {"events": [], "state": self.result_state}


class ModelAccessCase(GovernanceCase):
    def setUp(self):
        super().setUp()
        self.provider = ModeldDouble()
        self.provider_patch = patch("ai_union.model_service.ModelServiceClient", return_value=self.provider)
        self.provider_patch.start()
        self.addCleanup(self.provider_patch.stop)
        self.prepare()
        self.provider.au_id = self.au_id
        self.activate()

    def models(self, token="current"):
        status, value, _ = self.request("/api/v1/models?organization_id=" + self.au_id, token=token)
        self.assertEqual(status, 200, value)
        return value

    def model_command(self, kind, data, request_id=None, token="current", version=None):
        if version is None:
            version = self.read(token)["au"]["version"]
        request = {"id": request_id or str(uuid.uuid4()), "organization_id": self.au_id,
                   "base_version": version, "kind": kind, "data": copy.deepcopy(data)}
        status, value, _ = self.request("/api/v1/models/commands", request, token)
        return status, value, request

    def model_success(self, kind, data, **kwargs):
        status, value, request = self.model_command(kind, data, **kwargs)
        self.assertEqual(status, 200, value)
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        return value["receipt"], request

    def saved(self, request_id=None, profile="modeld_grant"):
        data = {"connection_id": "connection-a", "expected_revision": 0, "name": "Test connection", "profile": profile,
                "model": "model-a", "max_output_tokens": 256}
        if profile == "modeld_grant":
            data.update(grant_ref="grant-a", grant_revision=1)
        else:
            data.update(base_url="https://model.example.invalid/v1", api_key="s02-controlled-private-api-key")
        receipt, request = self.model_success("save_connection", data, request_id=request_id)
        self.wait_operation(receipt["operation_id"])
        return receipt, request

    def wait_operation(self, operation_id):
        return self.wait_for("operations", operation_id)

    def wait_for(self, table, key, *, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = next((x for x in self.models()[table] if x["id"] == key), None)
            if value and value["status"] not in ("queued", "running", "saving"):
                return value
            time.sleep(0.01)
        self.fail("Bounded test job did not complete: " + str(value))

    def allow_documents(self):
        charter = copy.deepcopy(self.read()["au"]["charter"])
        charter["allowed_tools"].append("read_document")
        self.success("amend_charter", {"charter": charter, "reason": "Authorize the selected read-only test material"})

    def resource_grant(self, max_calls=6):
        return self.model_success("grant_model_resources", {"max_calls": max_calls, "allow_unknown_cost": True,
            "reason": "Only bounded connection verification; provider cost may remain unknown"})

    def start_check(self, request_id=None):
        return self.model_success("start_model_check", {"connection_id": "connection-a", "expected_revision": 1,
            "binding_id": None, "document_name": "sample.txt", "document_text": "这是明确选择的真实本地资料，读取后概括。"}, request_id=request_id)
