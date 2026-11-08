"""Independent U097 boundary probes; real local HTTP, explicit model double only."""
import copy
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(sys.argv.pop(1)).resolve()))
from tests.test_core_model_events import CoreModelEventsTests
from ai_union.model_service import ServiceError


class IndependentEventsReview(CoreModelEventsTests):
    def test_logout_during_grant_lookup_never_returns_prior_body(self):
        self.seeded()
        before_posts = copy.deepcopy(self.provider.posts)
        original = self.provider.call
        def logout(method, path, *args, **kwargs):
            result = original(method, path, *args, **kwargs)
            if path.startswith('/v1/grants/'):
                self.assertEqual(self.request('/api/auth/logout', {})[0], 200)
            return result
        with patch.object(self.provider, 'call', side_effect=logout):
            status, result, _ = self.events()
        self.assertEqual(status, 401, result)
        self.assertNotIn('events', result)
        self.assertEqual(self.provider.posts, before_posts)

    def test_disable_during_grant_lookup_is_rechecked_before_body(self):
        self.seeded()
        before_posts = copy.deepcopy(self.provider.posts)
        original = self.provider.call
        fired = False
        def disable(method, path, *args, **kwargs):
            nonlocal fired
            result = original(method, path, *args, **kwargs)
            if path.startswith('/v1/grants/') and not fired:
                fired = True
                self.model_success('set_connection', {'connection_id': 'connection-a',
                    'expected_revision': 1, 'enabled': False, 'make_default': False})
            return result
        with patch.object(self.provider, 'call', side_effect=disable):
            status, result, _ = self.events()
        self.assertTrue(fired)
        self.assertEqual(status, 403, result)
        self.assertNotIn('events', result)
        self.assertEqual(self.provider.posts, before_posts)

    def test_private_payload_scope_tamper_is_not_redisclosed(self):
        self.seeded()
        with closing(sqlite3.connect(self.database())) as cx, cx:
            original = cx.execute('SELECT payload FROM model_attempts WHERE id=?', (self.attempt_id,)).fetchone()[0]
            value = json.loads(original)
            value['au_id'] = 'foreign-au'
            cx.execute('UPDATE model_attempts SET payload=? WHERE id=?', (json.dumps(value), self.attempt_id))
        try:
            before = self.dump()
            status, result, _ = self.events()
            self.assertEqual(status, 409, result)
            self.assertNotIn('events', result)
            self.assertEqual(self.dump(), before)
        finally:
            # Restore only the deliberately corrupted test input after asserting
            # fail-closed behavior, so the ordinary fixture shutdown can run.
            with closing(sqlite3.connect(self.database())) as cx, cx:
                cx.execute('UPDATE model_attempts SET payload=? WHERE id=?', (original, self.attempt_id))

    def test_current_grant_id_au_and_model_are_each_required(self):
        self.seeded()
        original = self.provider.call
        before, posts = self.dump(), copy.deepcopy(self.provider.posts)
        for change in ({'id': 'another-grant'}, {'au_id': 'another-au'}, {'model_ids': ['another-model']}):
            def wrong(method, path, *args, **kwargs):
                result = original(method, path, *args, **kwargs)
                return result | change if path.startswith('/v1/grants/') else result
            with self.subTest(change=change), patch.object(self.provider, 'call', side_effect=wrong):
                status, result, _ = self.events()
                self.assertEqual(status, 403, result)
                self.assertNotIn('events', result)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.provider.posts, posts)

    def test_unavailable_grant_service_cannot_fall_back_to_cached_body(self):
        self.seeded()
        before, posts = self.dump(), copy.deepcopy(self.provider.posts)
        with patch.object(self.provider, 'call', side_effect=ServiceError('unavailable', 503)):
            status, result, _ = self.events()
        self.assertEqual(status, 503, result)
        self.assertNotIn('events', result)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.provider.posts, posts)


if __name__ == '__main__':
    names = sorted(name for name in IndependentEventsReview.__dict__ if name.startswith('test_'))
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(IndependentEventsReview(name) for name in names))
    raise SystemExit(not result.wasSuccessful())
