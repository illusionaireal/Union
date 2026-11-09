"""Read the original Work step's modeld journal; never dispatch or settle it."""
from contextlib import closing
import copy
import sqlite3

from ..adapters.core_au_store import CoreAUStore
from ..domain import governance
from ..engine import identifier
from ..errors import CoreError, Rejected, require
from ..model_service import ServiceError

CONNECTION_FIELDS = ('id', 'revision', 'profile', 'model', 'grant_ref', 'grant_revision',
                     'max_output_tokens', 'task_ms')
ORIGIN_FIELDS = ('step_ref', 'attempt_id', 'command_id', 'model_request_id')


def connection_scope(connection):
    return {key: connection.get(key) for key in CONNECTION_FIELDS} if isinstance(connection, dict) else None


def readable_connection(state, step):
    original = step.get('connection')
    current = (state.get('model_access') or {}).get('connections', {}).get((original or {}).get('id'))
    return bool(step.get('command_id') and step.get('model_request_id') and current
                and current.get('enabled') and connection_scope(current) == connection_scope(original))


def _snapshot(service, token, au_id, work_id, step_ref, principal):
    app = service.app
    with app.mutex, app.read_catalog() as accounts:
        if app.identity.principal_in(accounts, token) != principal:
            raise CoreError('not_authenticated')
        directory, intent = app.governance.locate(au_id)
        with closing(sqlite3.connect((directory / 'state.sqlite3').as_uri() + '?mode=ro', uri=True)) as cx:
            cx.execute('PRAGMA query_only=ON')
            cx.execute('BEGIN')
            state = CoreAUStore.read_in(cx, au_id, creation=intent)['au']
            if governance.reader_role(state, principal) != 'governor':
                raise CoreError('not_authorized')
            work = (state.get('work_runtime') or {}).get('works', {}).get(work_id)
            step = next((s for s in (work or {}).get('steps', []) if s['step_ref'] == step_ref), None)
            if not step or not readable_connection(state, step):
                raise CoreError('not_authorized')
            require(any(a['id'] == step['attempt_id'] for a in work.get('attempts', [])), 'invalid_original_attempt')
            require(step.get('context_scope', {}).get('au_id') == au_id
                    and step.get('context_scope', {}).get('work_id') == work_id, 'invalid_original_work')
            return state['version'], copy.deepcopy({key: step[key] for key in ORIGIN_FIELDS}) | {
                'connection': connection_scope(step['connection'])}


def _remote(client, au_id, original):
    value = client.request(original['model_request_id'], au_id)
    require(isinstance(value, dict) and value.get('id') == original['model_request_id']
            and value.get('au_id') == au_id, 'invalid_original_response')
    if value.get('action_authorized') is not True:
        raise CoreError('not_authorized')
    require(value.get('state') in ('prepared', 'dispatching', 'queued', 'connecting', 'streaming',
                                  'running', 'completed', 'failed', 'interrupted', 'cancel_requested'), 'invalid_remote_state')
    return value


def _grant(service, client, au_id, connection):
    try:
        service.app.models.check_grant(client, au_id, connection)
    except Rejected as error:
        raise CoreError('not_authorized') from error


def read_events(service, token, au_id, work_id, step_ref, after='0', authorization_only='0'):
    principal = service.app.creation.principal(service.app.session(token))
    try:
        identifier(au_id); identifier(work_id)
        require(isinstance(step_ref, str) and 0 < len(step_ref) <= 256, 'invalid_step')
        require(isinstance(after, str) and after.isascii() and after.isdecimal() and len(after) <= 16,
                'invalid_cursor')
        cursor = int(after)
        require(cursor <= 9007199254740991, 'invalid_cursor')
        require(authorization_only in ('0', '1'), 'invalid_authority_mode')
    except (Rejected, TypeError, ValueError) as error:
        raise CoreError('invalid_request', '须提供原工作、原步进和非负整数游标') from error
    try:
        _, original = _snapshot(service, token, au_id, work_id, step_ref, principal)
        client = service.app.models.backend()
        _grant(service, client, au_id, original['connection'])
        _remote(client, au_id, original)
        # A display limit stops body loading, never the continuing read-authority check.
        page = ({'events': []} if authorization_only == '1' else
                client.events(original['model_request_id'], au_id, cursor))
        remote = _remote(client, au_id, original)
        _grant(service, client, au_id, original['connection'])
        version, current = _snapshot(service, token, au_id, work_id, step_ref, principal)
        if current != original:
            raise CoreError('not_authorized')
        require(isinstance(page, dict), 'invalid_event_page')
        raw = page.get('events')
        require(isinstance(raw, list) and len(raw) <= 500, 'invalid_events')
        by_seq = {}
        for item in raw:
            require(isinstance(item, dict) and item.get('request_id') == original['model_request_id']
                    and type(item.get('seq')) is int and 0 < item['seq'] <= 9007199254740991, 'invalid_event_identity')
            seq = item['seq']
            require(seq not in by_seq or by_seq[seq] == item, 'event_conflict')
            by_seq[seq] = item
        events, remaining, truncated = [], 65536, False
        for seq in sorted(by_seq):
            if seq <= cursor:
                continue
            item = by_seq[seq]
            payload = item.get('payload')
            if not isinstance(payload, dict):
                continue
            if item.get('type') == 'text_delta' and isinstance(payload.get('text'), str):
                text = payload['text'][:remaining]
                truncated |= len(text) != len(payload['text'])
                remaining -= len(text)
                events.append({'seq': seq, 'type': 'text_delta', 'text': text})
            elif item.get('type') == 'tool_call_complete' and payload.get('name') == 'read_document':
                events.append({'seq': seq, 'type': 'tool_call_complete', 'name': 'read_document'})
        next_cursor = max([cursor, *by_seq])
        has_more = len(raw) == 500
        require(not has_more or next_cursor > cursor, 'nonadvancing_page')
        return {'protocol': 'core.work-events.v1', 'organization_id': au_id, 'work_id': work_id,
                **original, 'version': version, 'access': {'principal_id': principal,
                'service_instance': service.app.instance}, 'source': 'persisted_modeld_events',
                'state': remote['state'], 'events': events, 'cursor': next_cursor, 'last_seq': next_cursor,
                'has_more': has_more, 'events_complete': False, 'authorization_only': authorization_only == '1',
                'truncated': truncated}
    except CoreError:
        raise
    except ServiceError as error:
        raise CoreError('not_authorized' if error.status in (401, 403, 404) else 'storage_unavailable',
                        '原模型观测暂不可读取；未重派发') from error
    except (Rejected, KeyError, TypeError, ValueError) as error:
        raise CoreError('incompatible_state', '原工作事件身份或内容不一致；请保留原请求核对') from error
    except (OSError, sqlite3.Error) as error:
        raise CoreError('storage_unavailable', '原工作事件暂不可读取') from error
