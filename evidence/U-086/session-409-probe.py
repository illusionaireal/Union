"""Read-only probe: one inconsistent catalog entry fails the whole /api/session.

Reproduces the window that produced every 117-byte snapshot-before-restart.json:
a catalog row still marked legacy_v0 while the AU's resolved engine refuses because
the directory is really core_v1. No product code is imported for behaviour change;
the probe only stubs Console collaborators.

Usage: python -B evidence/U-086/session-409-probe.py
Exit 0 = both cases behaved as documented below (i.e. the defect is reproduced and
the desired behaviour is still missing).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ai_union.console import Console  # noqa: E402
from ai_union.errors import CoreError  # noqa: E402


def stub_console(entries, creator=None, engine_error=None):
    console = object.__new__(Console)
    console.instance = 'service-probe'
    console.session = lambda token: {'role': 'board', 'principal_id': 'principal-probe',
                                    'organizations': None, 'view_id': 'view-probe'}

    class Creation:
        class catalog:
            @staticmethod
            def creator(au_id):
                return creator

        @staticmethod
        def read(session, au_id):
            raise CoreError('not_authorized')

    console.creation = Creation()
    console._catalog_entries = lambda: entries

    def engine(token, au_id):
        raise CoreError(engine_error or 'unsupported_capability')

    console.engine = engine
    return console


class SessionEndpointProbe(unittest.TestCase):
    def test_documented_defect_reproduces_409(self):
        """One legacy-marked row whose engine refuses fails the whole session read."""
        console = stub_console([{'id': 'au-inconsistent', 'profile': 'legacy_v0'}])
        with self.assertRaises(CoreError) as caught:
            console.session_info('token-probe')
        self.assertEqual(caught.exception.code, 'unsupported_capability')

    def test_desired_behaviour_skips_the_inconsistent_row(self):
        """DESIRED (not implemented): the healthy entry is still listed, HTTP 200."""
        console = stub_console([
            {'id': 'au-inconsistent', 'profile': 'legacy_v0'},
            {'id': 'au-healthy', 'profile': 'legacy_v0'},
        ])
        original = console.engine

        def engine(token, au_id):
            if au_id == 'au-inconsistent':
                return original(token, au_id)
            raise CoreError('not_authorized')

        console.engine = engine
        info = console.session_info('token-probe')  # currently raises -> RED
        self.assertEqual(info['core_protocol'], 'core.au.v1')


if __name__ == '__main__':
    unittest.main(verbosity=2)
