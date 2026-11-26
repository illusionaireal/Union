"""Schema five fences must prevent old code selection without migrating reads."""
import unittest
from unittest.mock import patch

from scripts import release_package as release
from tests.test_work_dispatch import WorkDispatchTests, CallbackTransport


class WorkRecoveryCompatibilityTests(WorkDispatchTests):
    def test_automatic_dispatch_requires_schema_five_and_refuses_old_schema_four_candidate(self):
        request = self.arrange()
        self.app.work.transport = CallbackTransport()
        self.app.work.run_step(self.token, request)
        self.assertEqual(self.state()["schema_version"], 5)
        before = self.dump()
        old = {"core_schemas": {"auth": 2, "catalog": 1}, "core_au_schemas": [1, 2, 3, 4]}
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(old, {"console_state": self.root})
        release.check_core_schemas(old | {"core_au_schemas": [1, 2, 3, 4, 5]}, {"console_state": self.root})
        self.assertEqual(self.dump(), before)

    def test_schema_four_marker_cannot_hide_current_execution_owner_from_installer(self):
        request = self.arrange()
        save = self.app.work.store.save
        def stale_marker(cx, state, charter, command, *args, **kwargs):
            if command["kind"].startswith("work_dispatch_"): state["schema_version"] = 4
            return save(cx, state, charter, command, *args, **kwargs)
        self.app.work.transport = CallbackTransport()
        with patch.object(self.app.work.store, "save", side_effect=stale_marker):
            self.app.work.run_step(self.token, request)
        before = self.dump()
        old = {"core_schemas": {"auth": 2, "catalog": 1}, "core_au_schemas": [1, 2, 3, 4]}
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(old, {"console_state": self.root})
        self.assertEqual(self.dump(), before)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkRecoveryCompatibilityTests(name)
                             for name in WorkRecoveryCompatibilityTests.__dict__ if name.startswith("test_"))
