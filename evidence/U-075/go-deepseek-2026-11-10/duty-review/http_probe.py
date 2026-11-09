"""Independent HTTP/SQLite boundary assertions, no real model or business data."""
import copy
import os
import sys
import importlib.util
import json
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

REPO = Path(os.environ.get("UNION_U075_REVIEW_ROOT", str(Path(__file__).resolve().parents[4])))
sys.path.insert(0, str(REPO))

from tests.model_access_support import ModelAccessCase
from ai_union.model_service import ServiceError

fixture_path = Path(os.environ.get("UNION_U075_REVIEW_FIXTURES", str(Path(__file__).resolve().parents[4] / "tests/test_core_model_events.py")))
spec = importlib.util.spec_from_file_location('pr73_cancel_fixture', fixture_path)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class IndependentCancelledHistory(ModelAccessCase):
    cancelled = fixture.CoreModelEventsTests.cancelled
    event = staticmethod(fixture.CoreModelEventsTests.event)
    events = fixture.CoreModelEventsTests.events

    def ready(self):
        self.saved(profile='openai_compatible')
        self.allow_documents()
        self.resource_grant(6)

    def stopped(self):
        self.cancelled()
        self.assertEqual(self.events()[0], 200, 'Current authorized cancelled history is the positive control')

    def test_original_stop_and_reopen_keep_exact_text_identity_and_reservation(self):
        self.stopped()
        before, posts = self.dump(), copy.deepcopy(self.provider.posts)
        first = self.events()[1]
        self.stop(); self.start()
        second = self.events()[1]
        self.assertEqual(first['events'], second['events'])
        for key, value in [('organization_id', self.au_id), ('check_id', self.check_id), ('attempt_id', self.attempt_id)]:
            self.assertEqual(second[key], value)
        self.assertEqual(second['access']['principal_id'], self.principal)
        self.assertEqual(self.models()['resources']['reserved_calls'], 1)
        self.assertEqual(self.provider.posts, posts)
        self.assertEqual(self.dump(), before)

    def test_cancel_does_not_bypass_wrong_live_grant_id_au_model_or_revision(self):
        self.stopped()
        original = self.provider.call
        for field, value in [('id', 'other-grant'), ('au_id', 'other-au'), ('model_ids', ['other-model']), ('revision', 2), ('revoked_at', 'now')]:
            with self.subTest(field=field):
                before, posts = self.dump(), copy.deepcopy(self.provider.posts)
                def wrong(method, path, *args, **kwargs):
                    result = original(method, path, *args, **kwargs)
                    return result | {field: value} if path.startswith('/v1/grants/') else result
                with patch.object(self.provider, 'call', side_effect=wrong):
                    status, body, _ = self.events()
                self.assertEqual(status, 403)
                self.assertNotIn('events', body)
                self.assertEqual(self.dump(), before)
                self.assertEqual(self.provider.posts, posts)

    def test_unavailable_current_grant_never_uses_cancelled_history_as_fallback(self):
        self.stopped()
        original = self.provider.call
        before, posts = self.dump(), copy.deepcopy(self.provider.posts)
        for code, expected in [(401,403), (403,403), (404,403), (500,503)]:
            with self.subTest(code=code):
                def unavailable(method, path, *args, **kwargs):
                    if path.startswith('/v1/grants/'):
                        raise ServiceError('independent-grant-unavailable', code)
                    return original(method, path, *args, **kwargs)
                with patch.object(self.provider, 'call', side_effect=unavailable):
                    status, body, _ = self.events()
                self.assertEqual(status, expected)
                self.assertNotIn('events', body)
                self.assertEqual(self.dump(), before)
                self.assertEqual(self.provider.posts, posts)

    def test_cancelled_remote_identity_digest_and_event_scope_still_fail_closed(self):
        self.stopped()
        with closing(sqlite3.connect(self.database())) as cx:
            raw = cx.execute('SELECT result FROM model_attempts WHERE id=?', (self.attempt_id,)).fetchone()[0]
        for field in ['id', 'au_id', 'request_digest', 'event_scope']:
            with self.subTest(field=field):
                remote = json.loads(raw)
                if field == 'event_scope':
                    remote['events'][0]['request_id'] = 'unrelated-original-request'
                else:
                    remote[field] = 'unrelated-original-fact'
                with closing(sqlite3.connect(self.database())) as cx, cx:
                    cx.execute('UPDATE model_attempts SET result=? WHERE id=?', (json.dumps(remote), self.attempt_id))
                before = self.dump()
                status, body, _ = self.events()
                self.assertEqual(status, 409)
                self.assertNotIn('events', body)
                self.assertEqual(self.dump(), before)

    def test_logout_during_grant_lookup_denies_cancelled_content(self):
        self.stopped()
        before, posts = self.dump(), copy.deepcopy(self.provider.posts)
        original = self.provider.call
        def logout(method, path, *args, **kwargs):
            result = original(method, path, *args, **kwargs)
            if path.startswith('/v1/grants/'):
                self.app.identity.logout(self.token)
            return result
        with patch.object(self.provider, 'call', side_effect=logout):
            status, body, _ = self.events()
        self.assertEqual(status, 401)
        self.assertNotIn('events', body)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.provider.posts, posts)

    def test_disable_during_grant_lookup_denies_cancelled_content(self):
        self.stopped()
        original = self.provider.call
        captured = []
        def disable(method, path, *args, **kwargs):
            result = original(method, path, *args, **kwargs)
            if path.startswith('/v1/grants/'):
                self.model_success('set_connection', {'connection_id':'connection-a', 'expected_revision':1, 'enabled':False, 'make_default':False})
                captured.append(self.dump())
            return result
        with patch.object(self.provider, 'call', side_effect=disable):
            status, body, _ = self.events()
        self.assertEqual(status, 403)
        self.assertNotIn('events', body)
        self.assertEqual(self.dump(), captured[-1])

    def test_cancelled_history_does_not_disclose_native_tool_arguments(self):
        self.stopped()
        with closing(sqlite3.connect(self.database())) as cx, cx:
            remote = json.loads(cx.execute('SELECT result FROM model_attempts WHERE id=?', (self.attempt_id,)).fetchone()[0])
            remote['events'].extend([
                self.event(self.attempt_id, 2, 'native_event', {'text':'independent-private-canary'}),
                self.event(self.attempt_id, 3, 'tool_call_complete', {'name':'read_document', 'arguments':'independent-private-canary'})])
            cx.execute('UPDATE model_attempts SET result=? WHERE id=?', (json.dumps(remote), self.attempt_id))
        before = self.dump()
        status, body, _ = self.events()
        self.assertEqual(status, 200)
        self.assertNotIn('independent-private-canary', json.dumps(body))
        self.assertEqual(body['events'][-1], {'seq':3,'type':'tool_call_complete','name':'read_document'})
        self.assertEqual(self.dump(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
