"""Independent HTTP/catalog probes; synthetic local fixtures, no model calls."""
import hashlib
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import unittest


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    candidate, output = map(Path, sys.argv[1:3])
    binding = json.loads(Path(__file__).with_name("source-manifest.json").read_text(encoding="utf-8"))
    unavailable = [name for name, expected in binding["files"].items()
                   if not (candidate / name).is_file() or digest(candidate / name) != expected]
    if unavailable:
        output.write_text(json.dumps({"status": "input_unavailable", "tests": 0,
                                     "candidate_imported": False, "files": unavailable}, indent=2), encoding="utf-8")
        return 2
    sys.path.insert(0, str(candidate.resolve()))
    from tests.test_core_creation import CoreCreationTests, creation
    from tests.support import CHARTER, RESOURCES

    observations = []

    class SessionCatalogProbes(CoreCreationTests):
        def legacy(self, label):
            token = self.app.new_session("board")
            receipt = self.app.command(token, {
                "id": "legacy-" + label, "organization_id": None, "base_version": None,
                "kind": "create", "data": {"name": label, "goal": "Synthetic catalog review",
                "board_name": "Synthetic owner", "charter": CHARTER, "resources": RESOURCES}})
            self.assertEqual(receipt["status"], "succeeded")
            return receipt["organization_id"]

        def state_path(self, au_id):
            with self.app.read_catalog() as cx:
                row = cx.execute("SELECT folder FROM organizations WHERE id=?", (au_id,)).fetchone()
            return self.root / row["folder"] / "state.sqlite3"

        def facts(self):
            with self.app.read_catalog() as cx:
                rows = [dict(r) for r in cx.execute("SELECT * FROM organizations ORDER BY id")]
                intents = [dict(r) for r in cx.execute("SELECT * FROM creations ORDER BY id")]
            state = {}
            for row in rows:
                with closing(sqlite3.connect(self.root / row["folder"] / "state.sqlite3")) as cx:
                    state[row["id"]] = cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0]
            return {"rows": rows, "intents": intents, "state": state}

        def mismatch_legacy(self, au_id):
            with closing(sqlite3.connect(self.state_path(au_id))) as cx, cx:
                original = cx.execute("SELECT data FROM state WHERE id=1").fetchone()[0]
                state = json.loads(original)
                state["runtime_profile"] = "core_v1"
                cx.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(state),))
            def restore_disposable_fixture():
                with closing(sqlite3.connect(self.state_path(au_id))) as cx, cx:
                    cx.execute("UPDATE state SET data=? WHERE id=1", (original,))
            self.addCleanup(restore_disposable_fixture)

        def observe(self, case, token="current"):
            before = self.facts()
            status, body, _ = self.request("/api/session", token=token)
            after = self.facts()
            actual = self.token if token == "current" else token
            try:
                self.app.session_info(actual)
                exception_type = None
            except Exception as error:
                exception_type = type(error).__name__
            observations.append({"case": case, "http_status": status,
                                 "error_code": body.get("code"), "direct_exception_type": exception_type,
                                 "listed_profiles": [r["profile"] for r in body.get("organizations", [])],
                                 "catalog_and_state_unchanged": before == after})
            self.assertEqual(before, after, "session read changed persisted identity/state")
            return status, body

        def test_healthy_core_and_legacy_are_listed(self):
            core = self.create()["organization_id"]
            legacy = self.legacy("healthy")
            status, body = self.observe("healthy_control")
            self.assertEqual(status, 200)
            self.assertEqual({r["id"] for r in body["organizations"]}, {core, legacy})

        def test_scope_does_not_admit_an_unrelated_inconsistent_au(self):
            healthy = self.legacy("scoped-healthy")
            bad = self.legacy("scoped-bad")
            self.mismatch_legacy(bad)
            token = self.app.new_session("observer", organizations=[healthy])
            status, body = self.observe("scope_control", token)
            self.assertEqual(status, 200)
            self.assertEqual([r["id"] for r in body["organizations"]], [healthy])

        def test_real_legacy_mismatch_keeps_healthy_session_available(self):
            healthy = self.create()["organization_id"]
            bad = self.legacy("bad-profile")
            self.mismatch_legacy(bad)
            self.assertIsNone(self.app.creation.catalog.creator(bad))
            status, body = self.observe("legacy_profile_mismatch")
            self.assertEqual(status, 200, "candidate did not isolate a real legacy catalog mismatch")
            self.assertIn(healthy, [r["id"] for r in body["organizations"]])

        def test_real_core_mismatch_keeps_healthy_session_available(self):
            bad = self.create(creation("core-bad"))["organization_id"]
            healthy = self.create(creation("core-healthy"))["organization_id"]
            with self.app.catalog() as cx:
                cx.execute("UPDATE organizations SET profile='legacy_v0' WHERE id=?", (bad,))
            def restore_disposable_fixture():
                with self.app.catalog() as cx:
                    cx.execute("UPDATE organizations SET profile='core_v1' WHERE id=?", (bad,))
            self.addCleanup(restore_disposable_fixture)
            self.assertIsNotNone(self.app.creation.catalog.creator(bad))
            status, body = self.observe("core_locator_profile_mismatch")
            self.assertEqual(status, 200, "candidate did not isolate a real Core catalog mismatch")
            self.assertIn(healthy, [r["id"] for r in body["organizations"]])

    names = ["test_healthy_core_and_legacy_are_listed", "test_scope_does_not_admit_an_unrelated_inconsistent_au",
             "test_real_legacy_mismatch_keeps_healthy_session_available", "test_real_core_mismatch_keeps_healthy_session_available"]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(SessionCatalogProbes(name) for name in names))
    unchanged = all(digest(candidate / name) == expected for name, expected in binding["files"].items())
    report = {"candidate": binding["commit"], "source_manifest_sha256": digest(Path(__file__).with_name("source-manifest.json")),
              "tests": result.testsRun,
              "passed": result.testsRun - len({test.id() for test, _ in result.failures + result.errors}),
              "failures": [test.id().split(".")[-1] for test, _ in result.failures],
              "errors": [test.id().split(".")[-1] for test, _ in result.errors],
              "observations": observations, "source_unchanged": unchanged, "real_model_calls": 0}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
