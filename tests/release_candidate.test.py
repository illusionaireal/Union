import importlib.util
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release", ROOT / "ops/release/release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class CandidateReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.source = self.work / "source"
        self.source.mkdir()
        directories = {"ai_union", "web/console", "ops/systemd", "scripts", "examples"}
        for entry in release.PAYLOAD_PATHS:
            target = self.source / entry
            if entry in directories:
                target.mkdir(parents=True, exist_ok=True)
                (target / "placeholder.txt").write_text("placeholder\n", encoding="utf-8")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("placeholder\n", encoding="utf-8")
        subprocess.run(["git", "init", "-b", "main"], cwd=self.source, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.source, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.source, check=True)
        subprocess.run(["git", "add", "."], cwd=self.source, check=True)
        subprocess.run(["git", "commit", "-m", "candidate fixture"], cwd=self.source, check=True, stdout=subprocess.DEVNULL)
        self.config = self.work / "release.json"
        self.config.write_text(json.dumps({"organization_root": "/var/lib/union/org", "console_root": "/var/lib/union/console", "listen_host": "127.0.0.1", "listen_port": 8766}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_build_verify_stage_activate_and_rollback(self):
        archive = release.build(self.source, self.work / "dist", "0.1.0-rc.1")
        verified = release.verify(archive, Path(str(archive) + ".sha256"))
        self.assertEqual(verified["version"], "0.1.0-rc.1")
        with tarfile.open(archive) as tar:
            self.assertFalse(any(".env" in name or ".union" in name for name in tar.getnames()))
        install = self.work / "install"
        staged = release.stage(archive, install, self.config)
        self.assertTrue((staged / "payload" / "ai_union").is_dir())
        self.assertEqual(release.activate(install, "0.1.0-rc.1", self.config), staged.resolve())
        second = release.build(self.source, self.work / "dist", "0.1.0-rc.2")
        release.stage(second, install, self.config)
        release.activate(install, "0.1.0-rc.2", self.config)
        self.assertEqual(release.activate(install, "0.1.0-rc.1", self.config), staged.resolve())

    def test_missing_config_makes_no_install_writes(self):
        archive = release.build(self.source, self.work / "dist", "0.1.0-rc.1")
        install = self.work / "install"
        with self.assertRaisesRegex(ValueError, "缺少宿主配置"):
            release.stage(archive, install, self.work / "missing.json")
        self.assertFalse(install.exists())

    def test_backup_is_private_archive(self):
        state = self.work / "state"; state.mkdir(); (state / "console.sqlite3").write_text("state", encoding="utf-8")
        archive = release.backup(state, self.work / "backups", "before-upgrade")
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        with tarfile.open(archive) as tar:
            self.assertIn("state/console.sqlite3", tar.getnames())


if __name__ == "__main__":
    unittest.main()
