"""Catalog identity checks must precede writes to an existing legacy AU."""
import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import patch

from ai_union.console import Console
from ai_union.corp import REQUEST_ID, company_engine
from ai_union.engine import Engine, Rejected, encoded
from tests.support import CHARTER, RESOURCES


class CatalogIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    @staticmethod
    def creation(label, request_id=None):
        return {"id": request_id or "create-" + label, "organization_id": None,
                "base_version": None, "kind": "create",
                "data": {"name": label, "goal": "preserve " + label,
                         "board_name": "fixture", "charter": CHARTER,
                         "resources": RESOURCES}}

    def pair(self, name, first_request_id=None):
        app = Console(Path(self.temp.name) / name)
        opened = [app]
        board = app.new_session("board")
        ids = []
        for label in ("A", "B"):
            receipt = app.command(board, self.creation(label, first_request_id if label == "A" else None))
            self.assertEqual(receipt["status"], "succeeded")
            ids.append(receipt["organization_id"])
        folders = {row["id"]: row["folder"] for row in app.organizations()}

        def cleanup():
            # Restore only the deliberately corrupted temporary test catalog.
            with app.catalog() as cx:
                for oid, folder in folders.items():
                    cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folder, oid))
            for instance in reversed(opened):
                instance.close()

        self.addCleanup(cleanup)
        return app, board, ids, folders, opened

    @staticmethod
    def contents(engine):
        with closing(sqlite3.connect(engine.db.as_uri() + "?mode=ro", uri=True)) as cx:
            database = tuple(cx.iterdump())
        # SQLite's transient WAL/SHM bookkeeping is not an AU business record.
        files = {str(path.relative_to(engine.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in engine.root.rglob("*")
                 if path.is_file() and not path.name.endswith(("-wal", "-shm"))}
        return database, files

    @staticmethod
    def seed_pending(engine, organization_id):
        engine.set_paused(False)
        pending = {"id": "pending-B", "organization_id": organization_id,
                   "base_version": 0, "kind": "start", "actor": "fixture",
                   "created_at": "2026-11-05T00:00:00+00:00",
                   "status": "accepted", "message": "original B receipt"}
        with engine.transaction() as cx:
            cx.execute("INSERT INTO commands VALUES(?,?,?)",
                       (pending["id"], encoded({"fixture": "B"}), encoded(pending)))
        return pending

    def test_wrong_au_mapping_rejects_open_recovery_and_close_before_writes(self):
        for boundary in ("open", "startup", "close"):
            app, board, (au_a, au_b), folders, opened = self.pair(boundary)
            scoped = app.new_session("board", organizations=[au_a])
            self.assertEqual(app.engine(scoped, au_a).state()["id"], au_a)
            victim = app.engine(board, au_b)
            if boundary == "startup":
                app.close()
            self.seed_pending(victim, au_b)
            (victim.root / "assets" / "preserve.txt").write_text("original B asset", encoding="utf-8")
            before = self.contents(victim)
            with app.catalog() as cx:
                cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folders[au_b], au_a))

            rejected = False
            try:
                if boundary == "open":
                    app.engine(scoped, au_a)
                elif boundary == "startup":
                    opened.append(Console(app.root))
                else:
                    app.close()
            except Rejected:
                rejected = True
            with self.subTest(boundary=boundary, guarantee="B remains unchanged"):
                self.assertEqual(self.contents(victim), before)
            with self.subTest(boundary=boundary, guarantee="mapping rejected"):
                self.assertTrue(rejected, "AU A must never open or write AU B through its catalog mapping")

    def test_valid_mapping_reopens_recovers_and_closes_the_original_aus(self):
        app, board, ids, folders, opened = self.pair("valid")
        engines = [app.engine(board, oid) for oid in ids]
        app.close()
        pending = self.seed_pending(engines[1], ids[1])
        reopened = Console(app.root)
        opened.append(reopened)
        board = reopened.new_session("board")
        self.assertEqual({row["id"] for row in reopened.session_info(board)["organizations"]}, set(ids))
        for oid, engine in zip(ids, engines):
            actual = reopened.engine(board, oid)
            self.assertEqual(actual.root, engine.root)
            self.assertEqual(actual.state()["id"], oid)
        recovered = reopened.receipt(board, ids[1], pending["id"])
        self.assertEqual(recovered["status"], "unknown")
        self.assertEqual(recovered["organization_id"], ids[1])
        self.assertEqual(engines[1].runs(), [])
        reopened.close()
        self.assertTrue(all(engine.paused() for engine in engines))
        self.assertEqual(folders, {row["id"]: row["folder"] for row in app.organizations()})

    def test_lifecycle_checks_late_bad_mapping_before_writing_an_earlier_valid_au(self):
        for boundary in ("startup", "close"):
            app, board, (au_a, au_b), folders, opened = self.pair("late-" + boundary)
            victim = app.engine(board, au_b)
            if boundary == "startup":
                app.close()
            self.seed_pending(victim, au_b)
            with app.catalog() as cx:
                cx.execute("DELETE FROM organizations WHERE id=?", (au_a,))
                cx.execute("INSERT INTO organizations VALUES(?,?)", (au_a, folders[au_b]))
            before = self.contents(victim)
            with self.subTest(boundary=boundary), self.assertRaises(Rejected):
                if boundary == "startup":
                    opened.append(Console(app.root))
                else:
                    app.close()
            self.assertEqual(self.contents(victim), before)

    def test_failed_startup_releases_the_lock_for_reopen_after_host_correction(self):
        app, _, (au_a, au_b), folders, opened = self.pair("startup-lock")
        app.close()
        with app.catalog() as cx:
            cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folders[au_b], au_a))
        with self.assertRaises(Rejected):
            Console(app.root)
        with app.catalog() as cx:
            cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folders[au_a], au_a))
        reopened = Console(app.root)
        opened.append(reopened)
        self.assertEqual({row["id"] for row in reopened.organizations()}, {au_a, au_b})

    def test_matching_id_outside_organizations_root_is_rejected_without_writes(self):
        app, board, (au_a, _), folders, _ = self.pair("escape")
        original = app.engine(board, au_a)
        outside = app.root / "outside"
        shutil.copytree(original.root, outside)
        copy = Engine(outside)
        before = self.contents(copy)
        for folder in ("organizations/../outside", str(outside), "../escape/outside"):
            with app.catalog() as cx:
                cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folder, au_a))
            with self.subTest(folder=folder), self.assertRaises(Rejected):
                app.engine(board, au_a)
            self.assertEqual(self.contents(copy), before)

    def test_missing_directory_or_database_is_rejected_without_creating_it(self):
        app, board, (au_a, _), _, _ = self.pair("missing")
        empty = app.root / "organizations" / "empty"
        empty.mkdir()
        for folder in ("organizations/absent", "organizations/empty"):
            with app.catalog() as cx:
                cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folder, au_a))
            with self.subTest(folder=folder), self.assertRaises(Rejected):
                app.engine(board, au_a)
            self.assertFalse((app.root / folder / "state.sqlite3").exists())
        self.assertFalse((app.root / "organizations" / "absent").exists())

    def test_catalog_list_checks_identity_while_scoped_session_keeps_its_own_au(self):
        app, board, (au_a, au_b), folders, _ = self.pair("listing")
        only_a = app.new_session("observer", organizations=[au_a])
        only_b = app.new_session("observer", organizations=[au_b])
        with app.catalog() as cx:
            cx.execute("UPDATE organizations SET folder=? WHERE id=?", (folders[au_b], au_a))
        with self.assertRaises(Rejected):
            app.organizations()
        with self.assertRaises(Rejected):
            app.session_info(only_a)
        self.assertEqual(app.session_info(only_b)["organizations"], [{"id": au_b, "name": "B"}])

    def test_unknown_profiles_schema_and_incomplete_state_do_not_fall_back_to_legacy(self):
        app, board, (au_a, _), _, _ = self.pair("incompatible")
        engine = app.engine(board, au_a)
        with engine.read_transaction() as cx:
            original = cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0]
        state = json.loads(original)
        cases = {
            "unknown-profile": encoded(state | {"runtime_profile": "future"}),
            "v1-is-not-legacy": encoded(state | {"runtime_profile": "core_v1", "schema_version": 1}),
            "null-profile": encoded(state | {"runtime_profile": None}),
            "unknown-schema": encoded(state | {"schema_version": 99}),
            "missing-id": encoded({key: value for key, value in state.items() if key != "id"}),
            "missing-work": encoded({key: value for key, value in state.items() if key != "work"}),
            "missing-resource-limits": encoded(state | {"resources": {}}),
            "invalid-json": "{",
            "invalid-state-type": "[]",
        }
        try:
            for name, value in cases.items():
                with engine.transaction() as cx:
                    cx.execute("UPDATE state SET data=? WHERE id=1", (value,))
                before = self.contents(engine)
                with self.subTest(case=name), self.assertRaises(Rejected):
                    app.engine(board, au_a)
                self.assertEqual(self.contents(engine), before)
        finally:
            with engine.transaction() as cx:
                cx.execute("UPDATE state SET data=? WHERE id=1", (original,))

    def test_catalog_profile_hint_is_checked_against_the_stored_profile(self):
        app, board, (au_a, _), _, _ = self.pair("profile-hint")
        engine = app.engine(board, au_a)
        with app.catalog() as cx:
            cx.execute("ALTER TABLE organizations ADD COLUMN profile TEXT DEFAULT 'legacy_v0'")
        with engine.transaction() as cx:
            state = engine._state(cx)
            cx.execute("UPDATE state SET data=? WHERE id=1", (encoded(state | {"runtime_profile": "legacy_v0"}),))
        self.assertEqual(app.engine(board, au_a).state()["id"], au_a)
        before = self.contents(engine)
        try:
            for hint in ("core_v1", "future", None):
                with app.catalog() as cx:
                    cx.execute("UPDATE organizations SET profile=? WHERE id=?", (hint, au_a))
                with self.subTest(hint=hint), self.assertRaises(Rejected):
                    app.engine(board, au_a)
                self.assertEqual(self.contents(engine), before)
        finally:
            with app.catalog() as cx:
                cx.execute("UPDATE organizations SET profile='legacy_v0' WHERE id=?", (au_a,))

    def test_state_database_link_cannot_escape_the_validated_directory(self):
        app, board, (au_a, _), _, _ = self.pair("database-link")
        engine = app.engine(board, au_a)
        target = app.root / "outside.sqlite3"
        engine.db.rename(target)
        try:
            try:
                engine.db.symlink_to(target)
            except OSError as error:
                self.skipTest("host cannot create a file symlink: " + str(error.errno))
            before = hashlib.sha256(target.read_bytes()).hexdigest()
            with self.assertRaises(Rejected):
                app.engine(board, au_a)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), before)
        finally:
            if engine.db.is_symlink():
                engine.db.unlink()
            target.rename(engine.db)

    def test_partial_database_is_rejected_instead_of_completed_on_open(self):
        app, board, (au_a, _), _, _ = self.pair("partial")
        state = app.engine(board, au_a).state()
        directory = app.root / "organizations" / "partial"
        directory.mkdir()
        with closing(sqlite3.connect(directory / "state.sqlite3")) as cx, cx:
            cx.execute("CREATE TABLE state(id INTEGER PRIMARY KEY,data TEXT NOT NULL)")
            cx.execute("INSERT INTO state VALUES(1,?)", (encoded(state),))
        partial = Engine(directory)
        before = self.contents(partial)
        with app.catalog() as cx:
            cx.execute("UPDATE organizations SET folder=? WHERE id=?", ("organizations/partial", au_a))
        with self.assertRaises(Rejected):
            app.engine(board, au_a)
        self.assertEqual(self.contents(partial), before)

    def test_incomplete_table_columns_reject_open_recovery_and_close_before_writes(self):
        schemas = {
            "events": "data TEXT NOT NULL",
            "runs": "id TEXT PRIMARY KEY, kind TEXT NOT NULL",
            "commands": "id TEXT PRIMARY KEY, receipt TEXT NOT NULL",
        }
        for table, columns in schemas.items():
            for boundary in ("open", "startup", "close"):
                app, board, (au_a, au_b), _, opened = self.pair(table + "-columns-" + boundary)
                malformed = app.engine(board, au_a)
                victim = app.engine(board, au_b)
                if boundary == "startup":
                    app.close()
                self.seed_pending(victim, au_b)
                with malformed.transaction() as cx:
                    cx.execute("ALTER TABLE " + table + " RENAME TO saved_table")
                    cx.execute("CREATE TABLE " + table + "(" + columns + ")")
                before = self.contents(malformed), self.contents(victim)
                try:
                    rejected = False
                    try:
                        if boundary == "open":
                            app.engine(board, au_a)
                        elif boundary == "startup":
                            opened.append(Console(app.root))
                        else:
                            app.close()
                    except Rejected:
                        rejected = True
                    with self.subTest(table=table, boundary=boundary, guarantee="no writes"):
                        self.assertEqual((self.contents(malformed), self.contents(victim)), before)
                    with self.subTest(table=table, boundary=boundary, guarantee="rejected"):
                        self.assertTrue(rejected, "an existing table name does not prove a complete legacy schema")
                finally:
                    # Only restore the deliberately malformed temporary database.
                    with malformed.transaction() as cx:
                        cx.execute("DROP TABLE " + table)
                        cx.execute("ALTER TABLE saved_table RENAME TO " + table)

    def test_missing_current_charter_or_legacy_authority_is_rejected_without_repair(self):
        app, board, (au_a, _), _, _ = self.pair("authority")
        engine = app.engine(board, au_a)
        with engine.read_transaction() as cx:
            charter = tuple(cx.execute("SELECT * FROM charters WHERE version=1").fetchone())
            board_hash = tuple(cx.execute("SELECT * FROM meta WHERE key='board_hash'").fetchone())
        for table, clause, original in (("charters", "version=1", charter),
                                        ("meta", "key='board_hash'", board_hash)):
            with engine.transaction() as cx:
                cx.execute("DELETE FROM " + table + " WHERE " + clause)
            before = self.contents(engine)
            try:
                with self.subTest(table=table), self.assertRaises(Rejected):
                    app.engine(board, au_a)
                self.assertEqual(self.contents(engine), before)
            finally:
                with engine.transaction() as cx:
                    cx.execute("INSERT INTO " + table + " VALUES(" + ",".join("?" for _ in original) + ")", original)

    def test_incomplete_current_charter_is_rejected_without_re_adoption(self):
        app, board, (au_a, _), _, _ = self.pair("charter-shape")
        engine = app.engine(board, au_a)
        with engine.transaction() as cx:
            original = cx.execute("SELECT data FROM charters WHERE version=1").fetchone()[0]
            cx.execute("UPDATE charters SET data='{}' WHERE version=1")
        before = self.contents(engine)
        try:
            with self.assertRaises(Rejected):
                app.engine(board, au_a)
            self.assertEqual(self.contents(engine), before)
        finally:
            with engine.transaction() as cx:
                cx.execute("UPDATE charters SET data=? WHERE version=1", (original,))

    def test_actual_id_mismatch_does_not_rewrite_the_state_or_catalog(self):
        app, board, (au_a, au_b), folders, _ = self.pair("stored-id")
        engine = app.engine(board, au_a)
        with engine.transaction() as cx:
            original = cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0]
            cx.execute("UPDATE state SET data=? WHERE id=1", (encoded(json.loads(original) | {"id": au_b}),))
        before = self.contents(engine)
        try:
            with self.assertRaises(Rejected):
                app.engine(board, au_a)
            self.assertEqual(self.contents(engine), before)
            with app.read_catalog() as cx:
                self.assertEqual(cx.execute("SELECT folder FROM organizations WHERE id=?", (au_a,)).fetchone()[0], folders[au_a])
        finally:
            with engine.transaction() as cx:
                cx.execute("UPDATE state SET data=? WHERE id=1", (original,))

    def test_creation_payloads_and_original_receipts_survive_restart_and_replay(self):
        app, board, ids, _, opened = self.pair("replay")
        with app.read_catalog() as cx:
            original = [tuple(row) for row in cx.execute("SELECT * FROM creations ORDER BY id")]
        receipts = [app.receipt(board, None, "create-" + label) for label in ("A", "B")]
        app.close()
        reopened = Console(app.root)
        opened.append(reopened)
        board = reopened.new_session("board")
        with patch("ai_union.console.validate_charter", side_effect=AssertionError("never revalidate an existing intent")):
            for label, receipt in zip(("A", "B"), receipts):
                self.assertEqual(reopened.command(board, self.creation(label)), receipt)
                self.assertEqual(reopened.receipt(board, None, receipt["id"]), receipt)
                changed = self.creation(label)
                changed["data"] = changed["data"] | {"name": "changed"}
                with self.assertRaises(Rejected):
                    reopened.command(board, changed)
        with reopened.read_catalog() as cx:
            self.assertEqual([tuple(row) for row in cx.execute("SELECT * FROM creations ORDER BY id")], original)
        self.assertEqual({row["id"] for row in reopened.organizations()}, set(ids))

    def test_unknown_creation_allocations_and_receipts_survive_restart_without_replay(self):
        for failure in ("storage", "registration"):
            app, board, _, _, opened = self.pair("unknown-" + failure)
            original_create = Engine.create
            original_catalog = app.catalog
            calls = 0

            def interrupted(*args, **kwargs):
                original_create(*args, **kwargs)
                raise OSError("fixture storage failure")

            @contextmanager
            def registration_failure():
                nonlocal calls
                calls += 1
                with original_catalog() as cx:
                    yield cx
                    if calls == 2:
                        raise sqlite3.OperationalError("fixture registration failure")

            fault = (patch.object(Engine, "create", side_effect=interrupted) if failure == "storage"
                     else patch.object(app, "catalog", registration_failure))
            request = self.creation("unknown")
            with fault:
                receipt = app.command(board, request)
            self.assertEqual(receipt["status"], "unknown")
            with app.read_catalog() as cx:
                row = tuple(cx.execute("SELECT payload,receipt,folder FROM creations WHERE id=?", (request["id"],)).fetchone())
            allocated = Engine(app.root / row[2])
            before = self.contents(allocated)
            app.close()
            reopened = Console(app.root)
            opened.append(reopened)
            board = reopened.new_session("board")
            with patch.object(Engine, "create", side_effect=AssertionError("unknown must not recreate")):
                self.assertEqual(reopened.command(board, request), receipt)
            self.assertEqual(reopened.receipt(board, None, request["id"]), receipt)
            self.assertEqual(self.contents(allocated), before)
            with reopened.read_catalog() as cx:
                self.assertEqual(tuple(cx.execute("SELECT payload,receipt,folder FROM creations WHERE id=?", (request["id"],)).fetchone()), row)
            self.assertEqual(len(reopened.organizations()), 2)
            self.assertEqual(len(list((app.root / "organizations").iterdir())), 3)
            if receipt["organization_id"]:
                with self.assertRaises(Rejected):
                    reopened.engine(board, receipt["organization_id"])

    def test_interrupted_accepted_creation_preserves_partial_files_and_original_intent(self):
        app, _, _, _, opened = self.pair("accepted-creation")
        request = self.creation("interrupted")
        folder = "organizations/" + hashlib.sha256(request["id"].encode()).hexdigest()
        directory = app.root / folder
        directory.mkdir()
        (directory / "partial.txt").write_bytes(b"original partial creation")
        receipt = {key: request[key] for key in ("id", "organization_id", "base_version", "kind")}
        receipt.update(status="accepted", actor="fixture", created_at="2026-11-05T00:00:00+00:00", message="accepted")
        with app.catalog() as cx:
            cx.execute("INSERT INTO creations VALUES(?,?,?,?)", (request["id"], encoded(request), encoded(receipt), folder))
        app.close()
        reopened = Console(app.root)
        opened.append(reopened)
        board = reopened.new_session("board")
        recovered = reopened.receipt(board, None, request["id"])
        self.assertEqual(recovered["status"], "unknown")
        self.assertIsNone(recovered["organization_id"])
        with patch.object(Engine, "create", side_effect=AssertionError("interrupted creation must not replay")):
            self.assertEqual(reopened.command(board, request), recovered)
        with reopened.read_catalog() as cx:
            saved = cx.execute("SELECT payload,folder FROM creations WHERE id=?", (request["id"],)).fetchone()
            self.assertEqual(tuple(saved), (encoded(request), folder))
        self.assertEqual([path.name for path in directory.iterdir()], ["partial.txt"])
        self.assertEqual((directory / "partial.txt").read_bytes(), b"original partial creation")

    def test_company_discovery_uses_the_same_profile_and_identity_boundary(self):
        app, board, (au_a, _), _, _ = self.pair("corp", first_request_id=REQUEST_ID)
        engine = company_engine(app.root)
        self.assertEqual(engine.state()["id"], au_a)
        with engine.transaction() as cx:
            original = cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0]
            cx.execute("UPDATE state SET data=? WHERE id=1", (encoded(json.loads(original) | {"runtime_profile": "future"}),))
        before = self.contents(engine)
        try:
            with self.assertRaises(Rejected):
                company_engine(app.root)
            self.assertEqual(self.contents(engine), before)
        finally:
            with engine.transaction() as cx:
                cx.execute("UPDATE state SET data=? WHERE id=1", (original,))


if __name__ == "__main__":
    unittest.main()
