"""Host model channel for one V1 work step: one step -> one persistent modeld request.

The protocol mirrors the legacy `ModelServiceTransport.chat` exactly (see
`ai_union/model_service.py`): create the request, poll the request and its
events, and read `result.message` / `result.usage` once the state is completed.

Failure contract used by the work runtime:

- `Rejected` means the request was definitely **not** executed (a 4xx/422 answer or
  a rejected payload), so no step fact may be invented.
- Any other exception means the outcome is unknown, so the caller keeps the
  reservation and asks an operator to reconcile.
"""
import copy
import time

from .errors import Rejected, require
from .model_service import ServiceError

TERMINAL = ("completed", "failed", "interrupted")
DEFINITE = (400, 401, 403, 404, 405, 413, 422)


class ModeldWorkTransport:
    def __init__(self, client, au_id, connection, *, timeout_seconds=60, poll_seconds=0.2,
                 sleep=time.sleep, clock=time.monotonic):
        self.client = client
        self.au_id = au_id
        self.connection = connection
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds
        self.sleep = sleep
        self.clock = clock

    def body(self, package, messages, tools):
        deadline = min(int(self.connection.get("task_ms") or self.timeout_seconds * 1000),
                       self.timeout_seconds * 1000)
        return {"id": self._request_id(package), "run_id": self._request_id(package), "au_id": self.au_id,
                "connection_id": self.connection["id"], "connection_revision": self.connection["revision"],
                "grant_ref": self.connection["grant_ref"], "grant_revision": self.connection["grant_revision"],
                "model_id": self.connection["model"], "messages": copy.deepcopy(messages),
                "tools": copy.deepcopy(tools),
                "generation": {"maxOutputTokens": self.connection["max_output_tokens"]},
                "deadlines": {"first_event_ms": 180000, "idle_ms": 120000, "task_ms": deadline}}

    @staticmethod
    def _request_id(package):
        value = str(package["run_id"]).replace("#", "-")
        require(all(character.isalnum() or character in "-_" for character in value),
                "步进标识不能用于模型请求")
        return value

    def chat(self, package, messages, tools):
        body = self.body(package, messages, tools)
        request_id = body["id"]
        try:
            self.client.call("POST", "/v1/requests", body)
        except ServiceError as error:
            if error.status in DEFINITE:
                raise Rejected("模型服务拒绝本次请求；本轮未执行，未产生步进事实") from None
            raise
        started = self.clock()
        after = 0
        while True:
            if self.clock() - started > self.timeout_seconds + 15:
                raise ServiceError("work_step_wait_expired")
            remote = self.client.request(request_id, self.au_id)
            require(remote.get("id") == request_id and remote.get("au_id") == self.au_id,
                    "模型服务回执范围不匹配")
            events = self.client.events(request_id, self.au_id, after).get("events", [])
            for event in events:
                require(event.get("request_id") == request_id and type(event.get("seq")) is int
                        and event["seq"] > after, "模型流事件标识或顺序不匹配")
                after = event["seq"]
            if remote["state"] in TERMINAL and len(events) < 500:
                break
            self.sleep(self.poll_seconds)
        if remote.get("action_authorized") is False:
            raise Rejected("原模型结果仅供核对；当前授权已失效，不能采用")
        if remote["state"] != "completed":
            raise ServiceError("work_step_" + str(remote["state"]))
        result = remote.get("result")
        require(isinstance(result, dict) and isinstance(result.get("message"), dict), "模型服务缺少完整结果")
        usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
        return result["message"], dict(usage)


def modeld_factory(config_file=None, *, timeout_seconds=60):
    """Host wiring: build the channel from the host-private modeld configuration."""
    def build(au_id, connection):
        from .model_service import ModelServiceClient
        require(isinstance(connection, dict), "该工作没有可用的模型连接")
        return ModeldWorkTransport(ModelServiceClient(config_file), au_id, connection,
                                   timeout_seconds=timeout_seconds)
    return build
