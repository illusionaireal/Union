"""Real catalogue/HTTP regression: one inconsistent row must not fail /api/session.

The duty review asked for a real catalogue/HTTP regression instead of stub-only
coverage. This module drives the real Console server and flips a created AU's
catalogue profile so the catalogue and the AU directory disagree; the session read
must still answer 200 instead of a whole-endpoint 409.
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

    def create_core_au(self):
        return self.create()['organization_id']

    def test_catalogue_directory_profile_mismatch_keeps_session_answerable(self):
        au_id = self.create_core_au()
        status, _, _ = self.request('/api/session')
        self.assertEqual(status, 200, 'baseline session read must succeed')

        with self.app.catalog() as cx:
            cx.execute("UPDATE organizations SET profile='legacy_v0' WHERE id=?", (au_id,))
        status, value, _ = self.request('/api/session')
        self.assertEqual(status, 200, value)
        listed = [item['id'] for item in value['organizations']]
        self.assertNotIn(au_id, listed, 'an unresolved row must be skipped, not listed')

    def test_damaged_legacy_state_still_keeps_the_endpoint_available(self):
        """A corrupt legacy state row is skipped; unrelated reads keep working."""
        au_id = self.create_core_au()
        with self.app.catalog() as cx:
            folder = cx.execute("SELECT folder FROM organizations WHERE id=?", (au_id,)).fetchone()['folder']
        database = self.root / folder / 'state.sqlite3'
        database.write_bytes(b'not a sqlite database')
        status, value, _ = self.request('/api/session')
        self.assertEqual(status, 200, value)
        self.assertNotIn(au_id, [item['id'] for item in value['organizations']])


if __name__ == '__main__':
    unittest.main()
