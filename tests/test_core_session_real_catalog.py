"""Real catalogue/HTTP regression: one inconsistent row must not fail /api/session.

The duty review asked for a real catalogue/HTTP regression instead of stub-only
coverage. This drives the real Console server: create an AU through the real command,
then flip its catalogue profile so the catalogue and the AU directory disagree. The
session read must still answer 200 and skip that row, while a damaged creation audit
keeps answering 409 (covered by tests/test_core_creation_failures.py).
"""
import unittest

from tests import test_core_creation as http


class CoreSessionRealCatalogTests(unittest.TestCase):
    setUp = http.CoreCreationTests.setUp
    start = http.CoreCreationTests.start
    stop = http.CoreCreationTests.stop
    request = http.CoreCreationTests.request
    setup_account = http.CoreCreationTests.setup_account
    create = http.CoreCreationTests.create

    def test_catalogue_profile_mismatch_keeps_the_session_answerable(self):
        au_id = self.create()['organization_id']
        self.assertEqual(self.request('/api/session')[0], 200, 'baseline session read')

        with self.app.catalog() as cx:
            cx.execute("UPDATE organizations SET profile='legacy_v0' WHERE id=?", (au_id,))
        try:
            status, value, _ = self.request('/api/session')
            self.assertEqual(status, 200, value)
            self.assertNotIn(au_id, [item['id'] for item in value['organizations']],
                             'an unresolvable row must be skipped, not listed')
            status, value, _ = self.request('/api/v1/aus/' + au_id)
            self.assertEqual(status, 409, value)
            self.assertEqual(value.get('code'), 'incompatible_state')
        finally:
            # Restore the row so fixture teardown can still close the console.
            with self.app.catalog() as cx:
                cx.execute("UPDATE organizations SET profile='core_v1' WHERE id=?", (au_id,))



if __name__ == '__main__':
    unittest.main()
