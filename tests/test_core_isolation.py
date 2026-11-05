"""Prepared AUs never enter legacy execution, including retained runtime handles."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid
from unittest.mock import patch

from ai_union.adapters.core_au_store import CoreAUStore
from ai_union.engine import Engine, Rejected, encoded, now
from tests.support import CHARTER, RESOURCES, init
from ai_union.runner import run


def files(root):
    # SQLite read-only WAL connections may create coordination sidecars. The
    # persisted AU and every application-owned file must remain unchanged.
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*')
            if path.is_file() and not path.name.endswith(('-wal', '-shm'))}


class CoreEngineIsolationTests(unittest.TestCase):
    def test_engine_rejects_prepared_unknown_and_incomplete_profiles_before_writes(self):
        for changes in ({}, {"runtime_profile": "future"}, {"schema_version": 2}, {"governance_root": None}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / 'au'
                CoreAUStore().create(root, {"name": "AU", "goal": "goal", "board_name": "display",
                    "charter": CHARTER, "resources": RESOURCES}, au_id='org-controlled', principal=str(uuid.uuid4()),
                    request_id='request', created_at=now())
                with closing(sqlite3.connect(root / 'state.sqlite3')) as cx, cx:
                    state = json.loads(cx.execute('SELECT data FROM state').fetchone()[0])
                    cx.execute('UPDATE state SET data=?', (encoded(state | changes),))
                before = files(root)
                with self.assertRaises(Rejected):
                    Engine(root)
                self.assertEqual(files(root), before)

    def test_existing_runtime_rechecks_profile_before_direct_sql_and_board_authority(self):
        for action in ('transaction', 'board', 'reserve'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                engine = init(root)
                old_state = engine.state()
                with closing(sqlite3.connect(engine.db)) as cx, cx:
                    cx.execute('UPDATE state SET data=?', (encoded(old_state | {'runtime_profile': 'future'}),))
                before = files(root)
                with self.assertRaises(Rejected):
                    if action == 'transaction':
                        with engine.transaction() as cx:
                            cx.execute("INSERT INTO meta VALUES('forbidden-direct-write','yes')")
                    else:
                        with closing(sqlite3.connect(engine.db)) as cx, cx:
                            cx.row_factory = sqlite3.Row
                            if action == 'board':
                                engine._board(cx, 'test-key')
                            else:
                                engine._reserve(cx, old_state, 'connection_test', 'fixture', {}, allow_paused=True)
                self.assertEqual(files(root), before)

    def test_retained_runner_handle_rejects_before_lock_activity_or_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine = init(root)
            state = engine.state()
            with closing(sqlite3.connect(engine.db)) as cx, cx:
                cx.execute('UPDATE state SET data=?', (encoded(state | {'runtime_profile': 'future'}),))
            before = files(root)
            with patch('ai_union.runner.step', side_effect=AssertionError('must not execute')):
                with self.assertRaises(Rejected):
                    run(engine, object(), 1)
            self.assertEqual(files(root), before)


if __name__ == '__main__':
    unittest.main()
