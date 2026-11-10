"""One inconsistent catalogue row must not fail the whole Core session read.

Background: creating a core_v1 AU briefly leaves a catalogue row marked legacy_v0
while its directory already resolves to core_v1. `Console._catalog_engine` then
refuses with `unsupported_capability`, and because `session_info` did not catch that
code the entire `/api/session` answered 409 — which is why every archived
`snapshot-before-restart.json` is the same 117-byte error body
(evidence/U-086/session-409-during-core-creation.md).

These tests pin the repaired behaviour: an inconsistent row is skipped like an
unauthorised one, other Core errors still surface, and a healthy entry is listed.
"""
import unittest

from ai_union.console import Console
from ai_union.errors import CoreError


def stub_console(entries, engine):
    console = object.__new__(Console)
    console.instance = 'service-test'
    console.fixture = None
    console.enable_codex = False
    console.enable_api = False
    console.session = lambda token: {'role': 'board', 'principal_id': 'principal-test',
                                    'organizations': None, 'view_id': 'view-test'}

    class Creation:
        class catalog:
            @staticmethod
            def creator(au_id):
                return None

        @staticmethod
        def read(session, au_id):
            raise CoreError('not_authorized')

    console.creation = Creation()
    console._catalog_entries = lambda: entries
    console.engine = engine
    return console


def refusing(code):
    def engine(token, au_id):
        raise CoreError(code)
    return engine


class SessionInconsistentCatalogueTests(unittest.TestCase):
    def test_inconsistent_legacy_row_is_skipped_instead_of_failing_the_session(self):
        console = stub_console([{'id': 'au-inconsistent', 'profile': 'legacy_v0'}],
                               refusing('unsupported_capability'))
        info = console.session_info('token-test')
        self.assertEqual(info['core_protocol'], 'core.au.v1')
        self.assertEqual(info['organizations'], [])

    def test_incompatible_state_row_is_also_skipped(self):
        console = stub_console([{'id': 'au-incompatible', 'profile': 'legacy_v0'}],
                               refusing('incompatible_state'))
        self.assertEqual(console.session_info('token-test')['organizations'], [])

    def test_other_core_errors_still_surface(self):
        console = stub_console([{'id': 'au-broken', 'profile': 'legacy_v0'}],
                               refusing('storage_unavailable'))
        with self.assertRaises(CoreError) as caught:
            console.session_info('token-test')
        self.assertEqual(caught.exception.code, 'storage_unavailable')

    def test_a_mixed_catalogue_still_lists_the_healthy_entry(self):
        entries = [{'id': 'au-inconsistent', 'profile': 'legacy_v0'},
                   {'id': 'au-healthy', 'profile': 'legacy_v0'}]

        class FakeEngine:
            def __init__(self, au_id):
                self.au_id = au_id

            def read_transaction(self):
                class Context:
                    def __enter__(self):
                        return object()

                    def __exit__(self, *exc):
                        return False
                return Context()

            def _state(self, cx):
                return {'id': self.au_id, 'name': '健康网关'}

        def engine(token, au_id):
            if au_id == 'au-inconsistent':
                raise CoreError('unsupported_capability')
            return FakeEngine(au_id)

        console = stub_console(entries, engine)
        info = console.session_info('token-test')
        self.assertEqual(info['organizations'],
                         [{'id': 'au-healthy', 'name': '健康网关', 'profile': 'legacy_v0'}])

    def test_unauthorised_engine_rows_still_surface_as_before(self):
        console = stub_console([{'id': 'au-unauthorised', 'profile': 'legacy_v0'}],
                               refusing('not_authorized'))
        with self.assertRaises(CoreError) as caught:
            console.session_info('token-test')
        self.assertEqual(caught.exception.code, 'not_authorized')


if __name__ == '__main__':
    unittest.main()
