"""Read-only, scoped text projection of the existing durable S02 event journal."""
import copy

from ..adapters.core_au_store import CoreAUStore
from ..adapters.model_access_store import ModelAccessStore
from ..domain import governance
from ..engine import identifier
from ..errors import CoreError, Rejected, require
from ..model_service import ServiceError


def _snapshot(service, token, au_id, check_id, attempt_id, principal, expected=None):
    app = service.app
    with app.mutex, app.read_catalog() as accounts:
        if app.identity.principal_in(accounts, token) != principal:
            raise CoreError("not_authenticated")
        directory, intent = app.governance.locate(au_id)
        with service.store.transaction(directory) as cx:
            state = CoreAUStore.read_in(cx, au_id, creation=intent)["au"]
            if governance.reader_role(state, principal) != "governor":
                raise CoreError("not_authorized")
            models = state.get("model_access", {})
            check = models.get("checks", {}).get(check_id)
            if not check or attempt_id not in check["attempt_ids"]:
                raise CoreError("not_authorized")
            config = models["connections"].get(check["connection_id"])
            config = ({key: config[key] for key in ("id", "revision", "enabled", "profile", "model", "grant_ref", "grant_revision")}
                      if config else None)
            if (not config or not config["enabled"] or config["revision"] != check["connection_revision"]
                    or (expected is not None and config != expected)):
                raise CoreError("not_authorized")
            if expected is None:
                return copy.deepcopy(config)
            private = ModelAccessStore.attempt(cx, attempt_id)
            remote = private["result"]
            if remote is not None:
                require(remote.get("id") == attempt_id and remote.get("au_id") == au_id
                        and remote.get("request_digest") == private["digest"], "event_identity_mismatch")
                if remote.get("action_authorized") is False:
                    raise CoreError("not_authorized")
            attempt = next(a for a in check["attempts"] if a["id"] == attempt_id)
            return state["version"], attempt["state"], remote


def read_events(service, token, au_id, check_id, attempt_id, after="0"):
    principal = service.app.creation.principal(service.app.session(token))
    try:
        for value in (au_id, check_id, attempt_id):
            identifier(value)
        require(isinstance(after, str) and after.isascii() and after.isdecimal()
                and len(after) <= 16, "invalid_cursor")
        cursor = int(after)
    except (Rejected, TypeError, ValueError) as error:
        raise CoreError("invalid_request", "须提供原验证、原调用和非负整数游标") from error
    try:
        config = _snapshot(service, token, au_id, check_id, attempt_id, principal)
        # No network operation holds the account/AU lock. This GET cannot dispatch.
        try:
            service.check_grant(service.backend(), au_id, config)
        except ServiceError as error:
            raise CoreError("not_authorized" if error.status in (401, 403, 404) else "storage_unavailable",
                            "暂时无法确认原模型授权；未读取生成内容") from error
        except Rejected as error:
            raise CoreError("not_authorized") from error
        version, state, remote = _snapshot(service, token, au_id, check_id, attempt_id, principal, config)
        remote = remote or {}
        raw = remote.get("events", [])
        require(isinstance(raw, list), "invalid_events")
        by_seq = {}
        for event in raw:
            require(isinstance(event, dict) and event.get("request_id") == attempt_id
                    and type(event.get("seq")) is int and event["seq"] > 0, "invalid_event_scope")
            seq = event["seq"]
            require(seq not in by_seq or by_seq[seq] == event, "event_conflict")
            by_seq[seq] = event
        last_seq = max(by_seq, default=0)
        if cursor > last_seq:
            raise CoreError("invalid_request", "游标超过已保存的原事件；请从起点查询")
        page = sorted(seq for seq in by_seq if seq > cursor)[:500]
        events, truncated = [], False
        remaining = 65536
        for seq in page:
            event = by_seq[seq]
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if event.get("type") == "text_delta" and isinstance(payload.get("text"), str):
                content = payload["text"][:remaining]
                truncated |= len(content) != len(payload["text"])
                remaining -= len(content)
                events.append({"seq": seq, "type": "text_delta", "text": content})
            elif event.get("type") == "tool_call_complete" and payload.get("name") == "read_document":
                events.append({"seq": seq, "type": "tool_call_complete", "name": "read_document"})
        cursor = page[-1] if page else cursor
        return {"protocol": "core.model-events.v1", "organization_id": au_id,
                "check_id": check_id, "attempt_id": attempt_id, "version": version,
                "access": {"principal_id": principal, "service_instance": service.app.instance},
                "state": state, "source": "persisted_modeld_events", "events": events,
                "cursor": cursor, "last_seq": last_seq, "has_more": cursor < last_seq,
                "events_complete": remote.get("events_complete") is True, "truncated": truncated}
    except CoreError:
        raise
    except (Rejected, KeyError, TypeError, ValueError) as error:
        raise CoreError("incompatible_state", "原模型事件不完整或身份不一致；请保留原请求核对") from error
    except OSError as error:
        raise CoreError("storage_unavailable", "原模型事件暂不可读取") from error
