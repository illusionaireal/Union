"""Actual disposable browser-host lifecycle, including unittest cleanups."""
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import u108_work_events_host as host


class BrowserHostLifecycleTests(unittest.TestCase):
    def test_stop_closes_console_and_removes_temporary_roots(self):
        case = host.WorkEventsTests()
        # Cleanup also runs after a failing assertion on the original host.
        self.addCleanup(case.doCleanups)
        with patch.object(host, 'WorkEventsTests', return_value=case), \
                patch('sys.stdin', io.StringIO('stop\n')), patch('sys.stdout', io.StringIO()):
            host.main()
        self.assertTrue(case.app.closed)
        self.assertIsNone(case.server)
        self.assertFalse(Path(case.root).exists())
        self.assertFalse(Path(case.tokens.name).exists())
