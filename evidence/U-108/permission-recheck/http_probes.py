"""Independent PR50 read-boundary probes: temporary HTTP/SQLite, no real inference."""
import unittest
from unittest.mock import patch

from tests.test_core_work_events import WorkEventsTests, RealClient


class IndependentWorkEvents(WorkEventsTests):
    def test_original_read_survives_unrelated_default_change(self):
        self.seeded()
        receipt, _ = self.model_success('save_connection', {
            'connection_id': 'other-connection', 'expected_revision': 0,
            'name': 'Other default', 'profile': 'modeld_grant', 'model': 'model-a',
            'grant_ref': 'grant-a', 'grant_revision': 1, 'max_output_tokens': 100})
        self.assertEqual(self.wait_operation(receipt['operation_id'])['status'], 'succeeded')
        self.model_success('set_connection', {'connection_id': 'other-connection',
            'expected_revision': 1, 'enabled': True, 'make_default': True})
        before, posts = self.dump(), len(self.model_posts())
        status, value, _ = self.observe()
        self.assertEqual(status, 200, value)
        self.assertEqual(value['connection']['id'], self.step['connection']['id'])
        self.assertEqual((self.dump(), len(self.model_posts())), (before, posts))

    def test_remote_revocation_during_events_prevents_disclosure(self):
        self.seeded()
        before, posts = self.dump(), len(self.model_posts())
        events = RealClient.events

        def revoke(client, *args):
            page = events(client, *args)
            self.remote_authorized = False
            return page

        with patch.object(RealClient, 'events', revoke):
            status, value, _ = self.observe()
        self.assertEqual(status, 403, value)
        self.assertNotIn('events', value)
        self.assertEqual((self.dump(), len(self.model_posts())), (before, posts))

    def test_governance_handoff_during_events_prevents_disclosure(self):
        self.seeded()
        token, principal = self.participant('independent-successor')
        self.success('nominate_governor', {'principal_id': principal, 'reason': 'review'})
        events = RealClient.events
        posts = len(self.model_posts())

        def handoff(client, *args):
            page = events(client, *args)
            self.success('accept_governance', {'reason': 'review'}, token=token)
            return page

        with patch.object(RealClient, 'events', handoff):
            status, value, _ = self.observe()
        self.assertEqual(status, 403, value)
        self.assertNotIn('events', value)
        self.assertEqual(len(self.model_posts()), posts)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(IndependentWorkEvents(name) for name in IndependentWorkEvents.__dict__
                              if name.startswith('test_'))
