"""Real local SDK checkpoint fixtures, observed without model calls or recovery."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.sqlite import SqliteSaver

from ai_union.engine import Engine
from ai_union.harness import session_tables
from ai_union.observation import snapshot
from ai_union.runtime_view import _checkpoint
from tests.support import decision, init, organization


class RuntimeCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.e, self.package = self.engine("org", "blocked")

    def engine(self, name, status):
        engine = init(Path(self.temp.name) / name)
        organization(engine)
        package = engine.begin_work("w1", "fixture")
        if status == "blocked":
            engine.finish_work(package["run_id"], {"status": "blocked", "summary": "Fixture input needed"}, {})
        elif status in ("unknown", "reconciled"):
            engine.fail_run(package["run_id"], "Fixture unknown", unknown=True)
            if status == "reconciled":
                engine.reconcile("test-key", package["run_id"], "confirmed_not_executed", "Fixture receipt checked")
        return engine, package

    def session(self, status="paused", engine=None, package=None):
        engine, package = engine or self.e, package or self.package
        with engine.transaction() as cx:
            session_tables(cx)
            cx.execute("INSERT OR REPLACE INTO agent_sessions(id,task_key,status,last_run_id,feedback,updated_at) VALUES(?,?,?,?,?,?)",
                       ("fixture-session", "fixture-key", status, package["run_id"], "PRIVATE_SESSION_FEEDBACK", "2026-10-31T00:00:00Z"))

    def checkpoint(self, *, engine=None, sid="fixture-session", namespace="", connection=None, keep_open=False, wal=False):
        engine = engine or self.e
        path = engine.root / "harness" / "checkpoints.sqlite3"
        path.parent.mkdir(exist_ok=True)
        def write(cx):
            checkpoint = empty_checkpoint()
            checkpoint["channel_values"] = {"private": "PRIVATE_CHECKPOINT_BODY"}
            SqliteSaver(cx).put({"configurable": {"thread_id": sid, "checkpoint_ns": namespace}}, checkpoint,
                               {"source": "input", "step": -1, "parents": {}, "private": "PRIVATE_CHECKPOINT_METADATA"}, {})
            if not wal:
                # Explicit non-WAL positive fixture; production SDK stays WAL.
                self.assertEqual(cx.execute("PRAGMA journal_mode=DELETE").fetchone()[0], "delete")
        if connection is not None:
            write(connection)
        elif keep_open:
            cx = sqlite3.connect(path)
            self.addCleanup(cx.close)
            write(cx)
        else:
            with closing(sqlite3.connect(path)) as cx:
                write(cx)
        return path

    def persisted(self, engine):
        with engine.read_transaction() as cx:
            tables = [r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            sessions = [dict(r) for r in cx.execute("SELECT * FROM agent_sessions ORDER BY rowid")] if "agent_sessions" in tables else []
        folder = engine.root / "harness"
        files = {p.name: None if p.name.endswith('-shm') else hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in folder.iterdir() if p.is_file()} if folder.is_dir() else {}
        return engine.state(), engine.events(), engine.runs(), tables, sessions, folder.exists(), files

    def observe(self, *, engine=None, member_id="m1"):
        engine = engine or self.e
        before = self.persisted(engine)
        result = None
        with patch.object(SqliteSaver, "setup", side_effect=AssertionError("Observation must not initialize SDK")), \
             patch.object(SqliteSaver, "get_tuple", side_effect=AssertionError("Observation must not load checkpoint bodies")):
            for reader in (engine, Engine(engine.root), engine):
                view = snapshot(reader)
                result = next(m for m in view["member_execution"] if m["member_id"] == member_id)["session"]
                self.assertEqual(view["budget"]["calls_reserved"], len(before[2]))
                public = json.dumps(view)
                for private in ("PRIVATE_CHECKPOINT_BODY", "PRIVATE_CHECKPOINT_METADATA", "PRIVATE_SESSION_FEEDBACK", "PRIVATE_READ_ERROR", str(engine.root)):
                    self.assertNotIn(private, public)
        self.assertEqual(before, self.persisted(engine))
        return result

    def test_session_status_is_not_checkpoint_evidence(self):
        for status, resume in (("paused", "not_available"), ("running", "not_available"),
                               ("failed", "not_available"), ("completed", "not_available"),
                               ("unknown", "requires_reconciliation"), ("future-status", "unknown")):
            with self.subTest(status=status):
                self.session(status)
                observed = self.observe()
                self.assertIs(observed["has_checkpoint"], False)
                self.assertEqual(observed["resume_state"], resume)

    def test_present_sdk_store_does_not_claim_session_checkpoint_or_resume(self):
        self.checkpoint()
        for status, resume in (("paused", "unknown"), ("running", "unknown"),
                               ("failed", "unknown"), ("completed", "not_available"),
                               ("unknown", "requires_reconciliation"), ("future-status", "unknown")):
            with self.subTest(status=status):
                self.session(status)
                observed = self.observe()
                self.assertIsNone(observed["has_checkpoint"])
                self.assertEqual(observed["resume_state"], resume)

    def test_other_thread_namespace_and_au_are_not_this_session(self):
        self.session()
        other, _ = self.engine("other-au", "blocked")
        self.checkpoint(engine=other)
        self.assertIs(self.observe()["has_checkpoint"], False)
        self.checkpoint(sid="other-session")
        self.checkpoint(namespace="child-graph")
        self.assertIsNone(self.observe()["has_checkpoint"])
        self.checkpoint()
        self.assertIsNone(self.observe()["has_checkpoint"])

    def test_unknown_reconciled_and_running_runs_do_not_offer_resume(self):
        for status in ("unknown", "reconciled", "running"):
            for checkpoint in (False, True):
                with self.subTest(status=status, checkpoint=checkpoint):
                    engine, package = self.engine(status + str(checkpoint), status)
                    self.session(engine=engine, package=package)
                    if checkpoint:
                        self.checkpoint(engine=engine)
                    observed = self.observe(engine=engine)
                    self.assertIs(observed["has_checkpoint"], None if checkpoint else False)
                    self.assertEqual(observed["resume_state"], "not_available" if status == "running" else "requires_reconciliation")

    def test_empty_database_and_unreadable_schema_have_distinct_results(self):
        self.session()
        path = self.e.root / "harness" / "checkpoints.sqlite3"
        path.parent.mkdir()
        with closing(sqlite3.connect(path)) as cx:
            cx.execute("PRAGMA user_version=1")
        self.assertIsNone(self.observe()["has_checkpoint"])
        with closing(sqlite3.connect(path)) as cx:
            cx.execute("CREATE TABLE checkpoints(unsupported TEXT)")
        observed = self.observe()
        self.assertIsNone(observed["has_checkpoint"])
        self.assertEqual(observed["resume_state"], "unknown")
        path.write_bytes(b"PRIVATE_INVALID_DATABASE")
        self.assertIsNone(self.observe()["has_checkpoint"])
        path.unlink()
        self.checkpoint()  # Presence is unknown without any checkpoint connect.
        original, attempts = sqlite3.connect, []
        def unavailable(database, *args, **kwargs):
            if "checkpoints.sqlite3" in str(database):
                attempts.append(str(database))
                raise AssertionError("Observation must not connect")
            return original(database, *args, **kwargs)
        with patch("sqlite3.connect", side_effect=unavailable):
            self.assertIsNone(self.observe()["has_checkpoint"])
        self.assertEqual(attempts, [])

    def test_non_wal_store_is_unknown_without_opening_checkpoint_content(self):
        self.session()
        path = self.e.root / "harness" / "checkpoints.sqlite3"
        path.parent.mkdir()
        with closing(sqlite3.connect(path)) as writer:
            self.checkpoint(connection=writer)
            self.assertEqual(path.read_bytes()[18:20], b"\x01\x01")
            original, original_open, opened, contents = sqlite3.connect, Path.open, [], []
            def guarded(database, *args, **kwargs):
                if "checkpoints.sqlite3" in str(database):
                    opened.append(str(database))
                    raise AssertionError("Observation must not connect to the checkpoint store")
                return original(database, *args, **kwargs)
            def forbid_content(file, *args, **kwargs):
                if file == path:
                    contents.append(str(file))
                    raise AssertionError("Observation must not read the checkpoint header or body")
                return original_open(file, *args, **kwargs)
            before = self.persisted(self.e)
            with patch("sqlite3.connect", side_effect=guarded), patch.object(Path, "open", forbid_content), \
                 patch.object(SqliteSaver, "setup", side_effect=AssertionError("No SDK setup")), \
                 patch.object(SqliteSaver, "get_tuple", side_effect=AssertionError("No checkpoint body")):
                for engine in (self.e, Engine(self.e.root), self.e):
                    view = snapshot(engine)
                    self.assertIsNone(view["member_execution"][0]["session"]["has_checkpoint"])
            self.assertEqual(before, self.persisted(self.e))
            self.assertEqual(opened, [])
            self.assertEqual(contents, [])

    def test_closed_wal_database_is_unknown_without_creating_sidecars(self):
        self.session()
        path = self.checkpoint(keep_open=False, wal=True)
        self.assertFalse(Path(str(path) + "-wal").exists())
        self.assertFalse(Path(str(path) + "-shm").exists())
        observed = self.observe()
        self.assertIsNone(observed["has_checkpoint"])
        self.assertEqual(observed["resume_state"], "unknown")

    def test_wal_writer_closes_at_connect_without_observer_recreating_sidecars(self):
        path = self.e.root / "harness" / "checkpoints.sqlite3"
        path.parent.mkdir()
        writer = sqlite3.connect(path)
        self.addCleanup(writer.close)
        self.checkpoint(connection=writer, wal=True)

        def files():
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.parent.iterdir()}

        before, transition, opened = files(), [], []
        original = sqlite3.connect

        def close_writer(database, *args, **kwargs):
            opened.append(str(database))
            writer.close()  # Real last-writer checkpoint/removal after precheck.
            transition.append(files())
            return original(database, *args, **kwargs)

        with patch("sqlite3.connect", side_effect=close_writer):
            observed = _checkpoint(self.e.root, "fixture-session")
        self.assertEqual(files(), transition[-1] if transition else before)
        self.assertIsNone(observed)
        self.assertEqual(opened, [])

    def test_live_wal_is_unknown_without_any_checkpoint_sqlite_connection(self):
        path = self.e.root / "harness" / "checkpoints.sqlite3"
        path.parent.mkdir()
        with closing(sqlite3.connect(path)) as writer:
            self.checkpoint(connection=writer, wal=True)
            self.assertTrue(writer.execute("SELECT 1 FROM checkpoints WHERE thread_id='fixture-session'").fetchone())
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.parent.iterdir()}
            original, opened = sqlite3.connect, []

            def forbid_checkpoint(database, *args, **kwargs):
                if "checkpoints.sqlite3" in str(database):
                    opened.append(str(database))
                    raise sqlite3.OperationalError("Checkpoint must not be opened")
                return original(database, *args, **kwargs)

            with patch("sqlite3.connect", side_effect=forbid_checkpoint):
                for status, resume in (("paused", "unknown"), ("failed", "unknown"), ("unknown", "requires_reconciliation")):
                    self.session(status)
                    observed = self.observe()
                    self.assertIsNone(observed["has_checkpoint"])
                    self.assertEqual(observed["resume_state"], resume)
                self.assertIsNone(_checkpoint(self.e.root, "missing-session"))
            self.assertEqual(opened, [])
            self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.parent.iterdir()})

    def test_file_replaced_at_connect_does_not_create_observer_sidecars(self):
        path = self.checkpoint()
        other, _ = self.engine("replacement", "blocked")
        replacement = self.checkpoint(engine=other, wal=True)

        def files():
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.parent.iterdir()}

        before, transition, opened = files(), [], []
        original = sqlite3.connect
        def replace_at_connect(database, *args, **kwargs):
            opened.append(str(database))
            path.replace(path.with_name("previous.sqlite3"))
            replacement.replace(path)  # Real external replacement after DELETE precheck.
            transition.append(files())
            return original(database, *args, **kwargs)
        with patch("sqlite3.connect", side_effect=replace_at_connect):
            observed = _checkpoint(self.e.root, "fixture-session")
        self.assertEqual(files(), transition[-1] if transition else before)
        self.assertIsNone(observed)
        self.assertEqual(opened, [])

    def test_metadata_errors_and_nonregular_paths_are_unknown_not_absent(self):
        self.session()
        folder = self.e.root / "harness"
        path = folder / "checkpoints.sqlite3"
        self.assertIs(self.observe()["has_checkpoint"], False)
        folder.mkdir()
        self.assertIs(self.observe()["has_checkpoint"], False)
        path.mkdir()
        self.assertIsNone(self.observe()["has_checkpoint"])
        path.rmdir()
        target = Path(self.temp.name) / "private-target"
        target.write_text("PRIVATE_CHECKPOINT_BODY")
        try:
            path.symlink_to(target)
        except OSError:
            pass  # Symlink creation may be unavailable on Windows.
        else:
            self.assertIsNone(self.observe()["has_checkpoint"])
            path.unlink()
        path.write_bytes(b"PRIVATE_INVALID_DATABASE")
        original = Path.lstat
        for error in (PermissionError("PRIVATE_READ_ERROR"), OSError("PRIVATE_READ_ERROR")):
            def unavailable(file):
                if file == path:
                    raise error
                return original(file)
            with patch.object(Path, "lstat", unavailable):
                self.assertIsNone(self.observe()["has_checkpoint"])
        path.unlink()
        folder.rmdir()
        folder.write_text("PRIVATE_CHECKPOINT_BODY")
        self.assertIsNone(self.observe()["has_checkpoint"])

    def test_legacy_read_and_handoff_do_not_create_or_share_checkpoints(self):
        self.assertEqual(self.observe(), {"id": None, "updated_at": None, "has_checkpoint": False, "resume_state": "not_available"})
        self.assertFalse((self.e.root / "harness").exists())
        self.session()
        self.checkpoint()
        self.e.apply_decision(decision(self.e, [{"op": "handoff", "position_id": "p1", "member_id": "m2", "assignment_id": "a3"}]), "m1", "a1")
        self.assertIsNone(self.observe(member_id="m2")["id"])
        self.assertIs(self.observe(member_id="m2")["has_checkpoint"], False)
        self.assertIsNone(self.observe()["has_checkpoint"])
