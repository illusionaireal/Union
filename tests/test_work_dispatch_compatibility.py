"""Safe code selection around actual S03 reservations; no real model requests."""
import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from ai_union.adapters.core_au_store import CoreAUStore
from ai_union.errors import CoreError
from scripts import release_package as release
from tests import test_work_dispatch as dispatch_support
from tests import test_governance_release as release_support


class WorkDispatchCompatibilityTests(dispatch_support.WorkDispatchTests):
    install = release_support.GovernanceReleaseTests.install

    def interrupt_call(self, request):
        def crash(package):
            raise KeyboardInterrupt("controlled loss after committing intent")
        self.app.work.transport = channel = dispatch_support.CallbackTransport(crash)
        with self.assertRaises(KeyboardInterrupt):
            self.app.work.run_step(self.token, request)
        return channel

    def test_committed_version_precedes_transport_and_original_facts_survive_reopen(self):
        request = self.arrange()
        original_root = copy.deepcopy(self.state()["governance_root"])
        observed = []
        self.app.work.transport = channel = dispatch_support.CallbackTransport(
            lambda package: observed.append(self.state()["schema_version"]))
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(observed, [4])
        self.assertEqual(receipt["status"], "succeeded")
        step = copy.deepcopy(self.card()["steps"][0])
        self.success("renew_governance", {"reason": "governance remains usable after dispatch"})
        revision = self.state()["model_access"]["connections"]["connection-a"]["revision"]
        self.model_success("set_connection", {"connection_id": "connection-a", "expected_revision": revision,
                                              "enabled": False, "make_default": False})
        self.assertEqual(self.state()["schema_version"], 4)
        self.stop()
        self.start()
        self.app.work.transport = channel
        self.assertEqual(self.app.work.run_step(self.token, request), receipt)
        self.assertEqual(len(channel.calls), 1)
        self.assertEqual(self.card()["steps"][0], step)
        self.assertEqual(self.state()["governance_root"], original_root)

    def test_interrupted_reservation_blocks_old_selection_and_already_selected_old_run(self):
        self.install("old", [1, 2, 3])
        self.install("current", [1, 2, 3, 4])
        # Only dependency probes are replaced; actual manifest and database gates run.
        with patch.object(release, "preflight", side_effect=lambda p, c: release.verify_directory(p)):
            release.activate("old", self.release_config, stopped=True)
            request = self.arrange()
            channel = self.interrupt_call(request)
            self.stop()
            before = self.dump()
            catalog = (self.root / "console.sqlite3").read_bytes()
            pointer = (self.release_config["installation_root"] / "current.json").read_bytes()
            with self.assertRaises(release.ReleaseError):
                release.activate("old", self.release_config, stopped=True)
            with patch.object(release.subprocess, "Popen") as spawn:
                with self.assertRaises(release.ReleaseError):
                    release.run("console", self.release_config)
                spawn.assert_not_called()
            self.assertEqual((self.release_config["installation_root"] / "current.json").read_bytes(), pointer)
            self.assertEqual((self.root / "console.sqlite3").read_bytes(), catalog)
            self.assertEqual(self.dump(), before)
            release.activate("current", self.release_config, stopped=True)
            self.assertEqual(self.dump(), before)
            self.assertEqual(len(channel.calls), 1)

    def test_parent_loop_preparation_alone_requires_compatible_code(self):
        request = self.arrange() | {"kind": "run_loop"}
        with patch.object(self.app.work, "drive_loop", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.app.work.run_loop(self.token, request)
        self.assertEqual(len(self.card()["loops"]), 1)
        self.assertEqual(self.card().get("steps", []), [])
        self.assertEqual(self.state()["schema_version"], 4)

    def test_failed_prepare_rolls_back_marker_and_intent_before_transport(self):
        request = self.arrange()
        before = self.dump()
        self.app.work.transport = channel = dispatch_support.CallbackTransport()
        original = self.app.work.store.save
        def fail(cx, state, charter, request, *args, **kwargs):
            original(cx, state, charter, request, *args, **kwargs)
            if request["kind"] == "work_dispatch_prepared":
                raise OSError("controlled commit failure")
        with patch.object(self.app.work.store, "save", side_effect=fail), self.assertRaises(OSError):
            self.app.work.run_step(self.token, request)
        self.assertEqual(channel.calls, [])
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.state()["schema_version"], 3)

    def test_rejected_admission_and_manual_steps_keep_prior_compatibility(self):
        request = self.arrange()
        self.app.work.transport = None
        self.app.work.transport_factory = None
        self.assertEqual(self.app.work.run_step(self.token, request)["status"], "rejected")
        _, response, _ = self.work_command(self.au_id, "reserve_step", {"work_id": "work-overview"})
        self.assertEqual(response["receipt"]["status"], "succeeded")
        step = self.card()["steps"][0]
        _, response, _ = self.work_command(self.au_id, "settle_step", {"work_id": "work-overview",
            "step_id": step["step_ref"], "status": "released", "reason": "manual preparation was never sent"})
        self.assertEqual(response["receipt"]["status"], "succeeded")
        self.assertEqual(self.state()["schema_version"], 3)
        manifest = {"core_schemas": {"auth": 2, "catalog": 1}, "core_au_schemas": [1, 2, 3]}
        release.check_core_schemas(manifest, {"console_state": self.root})

    def test_pre_marker_schema_three_intent_blocks_old_code_without_read_migration(self):
        request = self.arrange()
        original = self.app.work.store.save
        def historical_save(cx, state, charter, request, *args, **kwargs):
            # Generate the actual PR #17 schema-3 format, with a coherent audit chain.
            # Only this fixture writer predates the marker; release checks are real.
            if request["kind"].startswith("work_dispatch_"):
                state["schema_version"] = 3
            return original(cx, state, charter, request, *args, **kwargs)
        with patch.object(self.app.work.store, "save", side_effect=historical_save):
            self.interrupt_call(request)
        self.assertEqual(self.state()["schema_version"], 3)
        before = self.dump()
        manifest = {"core_schemas": {"auth": 2, "catalog": 1}, "core_au_schemas": [1, 2, 3]}
        with self.assertRaises(release.ReleaseError):
            release.check_core_schemas(manifest, {"console_state": self.root})
        release.check_core_schemas(manifest | {"core_au_schemas": [1, 2, 3, 4]}, {"console_state": self.root})
        self.assertEqual(self.dump(), before)

    def test_schema_four_still_validates_private_model_records(self):
        request = self.arrange()
        self.app.work.transport = dispatch_support.CallbackTransport()
        self.app.work.run_step(self.token, request)
        self.assertEqual(self.state()["schema_version"], 4)
        self.stop()
        with closing(sqlite3.connect(self.database())) as cx, cx:
            cx.execute("DROP TABLE model_attempts")
        with self.assertRaises(CoreError) as failure:
            CoreAUStore().read(self.directory, self.au_id, creation=self.intent)
        self.assertEqual(failure.exception.code, "incompatible_state")

    def test_package_declares_target_source_support_without_importing_that_source(self):
        from ai_union.domain import governance
        # These inert build files test packaging, never installation or execution.
        # Git metadata is controlled; source parsing, archive creation and digest
        # verification use the real release implementation and temporary files.
        source = self.root / "package-source"
        repository = Path(__file__).resolve().parents[1]
        payload = {
            "ai_union/server.py": b"# controlled source\n",
            "ai_union/domain/model_profiles.py": b"PROFILES = {'modeld_grant': {}}\n",
            "ai_union/domain/governance.py": (repository / "ai_union/domain/governance.py").read_bytes(),
            "data/model-catalog.json": b"{}",
            "services/modeld/upstream.lock.json": b"{}",
            "services/modeld/dist/upstream.lock.json": b"{}",
            "services/modeld/dist/main.js": b"// inert fixture\n",
            "services/modeld/dist/LICENSE.opencode": b"fixture",
            "services/modeld/dist/THIRD_PARTY_NOTICES.json": b"[]",
            "web/console/dist/index.html": b"<!-- inert fixture -->",
        }
        for name in ("scripts/release_package.py", "scripts/upgrade_core_identity.py",
                     "scripts/reset_owner.py", "ops/release/README.md", "ops/release/deployment.example.json"):
            payload[name] = b"# fixture\n"
        for name, content in payload.items():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        def metadata(args, **kwargs):
            if args[1] == "ls-files":
                return ("\0".join(payload) + "\0").encode()
            if args[1] == "rev-parse":
                return "0" * 40
            self.assertEqual(args[1:3], ["diff", "--name-only"])
            return b""

        with patch.object(release.subprocess, "check_output", side_effect=metadata), \
                patch.object(governance, "SUPPORTED_SCHEMAS", (2,), create=True):
            archive = self.root / "target-source.zip"
            manifest = release.pack(source, archive, "target-source")
            self.assertEqual(manifest["core_au_schemas"], [1, 2, 3, 4])
            self.assertEqual(release.verify_archive(archive)["core_au_schemas"], [1, 2, 3, 4])
            # A different source cannot inherit the packer's schema-4 support.
            (source / "ai_union/domain/governance.py").write_text(
                "SUPPORTED_SCHEMAS = (2, 3)\nraise RuntimeError('source must not execute')\n", encoding="utf-8")
            older = release.pack(source, self.root / "older-source.zip", "older-source")
            self.assertEqual(older["core_au_schemas"], [1, 2, 3])

    @unittest.skipUnless((Path(__file__).resolve().parents[1] / "services/modeld/dist/main.js").is_file(),
                         "Build modeld before checking its release declaration")
    def test_built_candidate_declares_durable_dispatch_support(self):
        from ai_union.domain import governance
        # Packaging must read the exact source tree, not an already imported runtime.
        with patch.object(governance, "SUPPORTED_SCHEMAS", (2,)):
            manifest = release.pack(Path(__file__).resolve().parents[1], self.root / "dispatch.zip", "dispatch-test")
        self.assertIn(4, manifest["core_au_schemas"])


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkDispatchCompatibilityTests(name)
                             for name in WorkDispatchCompatibilityTests.__dict__ if name.startswith("test_"))
