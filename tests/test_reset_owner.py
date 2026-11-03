"""Reset helper keeps business data, backs up the database and reopens the claim window."""
import importlib.util
import gc
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from ai_union.console import Console

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'reset_owner.py'
SPEC = importlib.util.spec_from_file_location('union_reset_owner', SCRIPT)
reset_owner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reset_owner)


class ResetOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Console(self.temp.name)
        self.addCleanup(lambda: self.app.close())
        self.app.identity.setup(None, 'owner', 'correct-horse-password', False)

    def test_reset_deletes_account_rows_and_keeps_a_private_backup(self):
        # A backup must be usable and releasable without waiting for GC to
        # close SQLite's cyclic connection objects (notably on Windows).
        gc_was_enabled = gc.isenabled()
        gc.disable()
        if gc_was_enabled:
            self.addCleanup(gc.enable)
        self.assertTrue(self.app.identity.configured())
        self.assertEqual(reset_owner.reset(self.temp.name, confirm=True), 0)
        self.assertFalse(self.app.identity.configured())
        backups = list(Path(self.temp.name).glob('console.sqlite3.bak-*'))
        self.assertEqual(len(backups), 1)
        if sys.platform != 'win32':
            self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
        with closing(sqlite3.connect(backups[0])) as saved:
            self.assertEqual(saved.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(saved.execute('SELECT COUNT(*) FROM owner_account').fetchone()[0], 1)
        # Windows refuses this while the backup connection still owns a handle.
        backups[0].unlink()

    def test_dry_run_keeps_the_account(self):
        self.assertEqual(reset_owner.reset(self.temp.name, confirm=False), 0)
        self.assertTrue(self.app.identity.configured())

    def test_foreign_database_is_rejected_before_writing(self):
        foreign = Path(self.temp.name) / 'foreign'
        foreign.mkdir()
        (foreign / 'console.sqlite3').write_bytes(b'not a union database')
        with self.assertRaises(SystemExit) as raised:
            reset_owner.reset(str(foreign), confirm=True)
        self.assertIn('数据库操作失败', str(raised.exception))
