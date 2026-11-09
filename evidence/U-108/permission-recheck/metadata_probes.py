"""Independent current-head metadata read checks; isolated HTTP/SQLite only."""
import unittest
from unittest.mock import patch

from tests.test_core_work_events import WorkEventsTests, RealClient


class MetadataReview(WorkEventsTests):
    def test_metadata_cursor_control_is_read_only_without_events(self):
        self.seeded()
        before, posts = self.dump(), len(self.model_posts())
        with patch.object(RealClient, 'events', side_effect=AssertionError('body read')):
            status, value, _ = self.observe(123, authorization_only='1')
        self.assertEqual(status, 200, value)
        self.assertEqual((value['cursor'], value['events'], value['authorization_only']), (123, [], True))
        for key in ('step_ref', 'attempt_id', 'command_id', 'model_request_id'):
            self.assertEqual(value[key], self.step[key])
        self.assertEqual((self.dump(), len(self.model_posts())), (before, posts))

    def test_revocation_between_metadata_request_reads_is_denied(self):
        self.seeded()
        before, posts = self.dump(), len(self.model_posts())
        original = RealClient.request
        reads = []
        def revoke(client, *args):
            value = original(client, *args)
            reads.append(args)
            if len(reads) == 1:
                self.remote_authorized = False
            return value
        with patch.object(RealClient, 'request', revoke), patch.object(
                RealClient, 'events', side_effect=AssertionError('body read')):
            status, value, _ = self.observe(authorization_only='1')
        self.assertEqual(status, 403, value)
        self.assertEqual(len(reads), 2)
        self.assertNotIn('events', value)
        self.assertEqual((self.dump(), len(self.model_posts())), (before, posts))

    def test_wrong_remote_identity_is_denied_in_metadata_mode(self):
        self.seeded()
        before, posts = self.dump(), len(self.model_posts())
        for fault in ('id', 'au'):
            self.fault = fault
            with patch.object(RealClient, 'events', side_effect=AssertionError('body read')):
                status, value, _ = self.observe(authorization_only='1')
            self.assertEqual(status, 409, value)
            self.assertNotIn('events', value)
        self.assertEqual((self.dump(), len(self.model_posts())), (before, posts))

    def test_handoff_during_metadata_read_denies_old_governor(self):
        self.seeded()
        token, principal = self.participant('metadata-successor')
        self.success('nominate_governor', {'principal_id': principal, 'reason': 'review'})
        posts = len(self.model_posts())
        self.grant_hook = lambda: self.success('accept_governance', {'reason': 'review'}, token=token)
        with patch.object(RealClient, 'events', side_effect=AssertionError('body read')):
            status, value, _ = self.observe(authorization_only='1')
        self.assertEqual(status, 403, value)
        self.assertNotIn('events', value)
        self.assertEqual(len(self.model_posts()), posts)

    def test_connection_disable_during_metadata_read_preserves_usage(self):
        self.seeded()
        posts = len(self.model_posts())
        self.grant_hook = lambda: self.model_success('set_connection', {
            'connection_id': 'connection-a', 'expected_revision': 1,
            'enabled': False, 'make_default': False})
        with patch.object(RealClient, 'events', side_effect=AssertionError('body read')):
            status, value, _ = self.observe(authorization_only='1')
        self.assertEqual(status, 403, value)
        card = self.request('/api/v1/work?organization_id=' + self.au_id)[1]['works'][0]
        self.assertEqual((card['budget']['used'], len(self.model_posts())), (1, posts))
        self.assertFalse(card['steps'][0]['can_observe'])


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(MetadataReview(name) for name in MetadataReview.__dict__
                              if name.startswith('test_'))
