"""Release failure behavior; no providers, accounts or real model requests."""
import copy
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import release_package as release


class ReleasePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'installation_root': self.root / 'code', 'console_state': self.root / 'business',
                       'modeld_config': self.root / 'private' / 'modeld.json',
                       'python': Path(__import__('sys').executable), 'bun': self.root / 'bun', 'console_port': 8766}

    def package(self, release_id='candidate-a', content=b'candidate-a', extra=None, manifest_change=None):
        payload = {'ai_union/__init__.py': content}
        manifest = {'schema_version': 1, 'release_id': release_id, 'git_baseline': '0' * 40,
                    'source_state': 'controlled', 'toolchain': {'bun': '1.4.2'},
                    'files': {p: {'size': len(b), 'sha256': release.digest(b)} for p, b in payload.items()}}
        if manifest_change:
            manifest_change(manifest)
        archive = self.root / (release_id + '.zip')
        with zipfile.ZipFile(archive, 'w') as z:
            for p, data in payload.items() | {'manifest.json': release.encoded(manifest)}.items():
                z.writestr(p, data)
            if extra:
                z.writestr(*extra)
        return archive

    def test_valid_python_dunder_path_installs_without_creating_business_state(self):
        archive = self.package()
        release.install(archive, self.config)
        installed = self.config['installation_root'] / 'releases/candidate-a'
        self.assertEqual(release.verify_directory(installed)['release_id'], 'candidate-a')
        self.assertFalse(self.config['console_state'].exists())
        self.assertFalse(self.config['modeld_config'].parent.exists())
        self.assertFalse((self.config['installation_root'] / 'current.json').exists())

    def test_bad_digest_rejected_before_installation_directory_is_created(self):
        archive = self.package(manifest_change=lambda m: m['files']['ai_union/__init__.py'].update(sha256='f' * 64))
        with self.assertRaises(release.ReleaseError):
            release.install(archive, self.config)
        self.assertFalse(self.config['installation_root'].exists())

    def test_traversal_extra_duplicate_and_link_members_are_rejected(self):
        for index, path in enumerate(('../escaped', 'C:/escaped', 'ai_union/../../escaped',
                                      'ai_union\\escaped', 'extra.txt', 'AI_UNION/__INIT__.PY')):
            with self.subTest(path=path), self.assertRaises(release.ReleaseError):
                release.verify_archive(self.package(f'bad-{index}', extra=(path, b'bad')))
        archive = self.package('bad-link')
        with zipfile.ZipFile(archive, 'a') as z:
            info = zipfile.ZipInfo('link')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, 'outside')
        with self.assertRaises(release.ReleaseError):
            release.verify_archive(archive)

    def test_installation_conflict_and_failed_extract_preserve_existing_version(self):
        archive = self.package()
        release.install(archive, self.config)
        with self.assertRaises(release.ReleaseError):
            release.install(archive, self.config)
        second = self.package('candidate-b')
        original = release.verify_directory
        def fail_staging(path):
            if Path(path).name.startswith('.staging-'):
                raise release.ReleaseError('controlled extraction failure')
            return original(path)
        with patch.object(release, 'verify_directory', side_effect=fail_staging), self.assertRaises(release.ReleaseError):
            release.install(second, self.config)
        folder = self.config['installation_root'] / 'releases'
        self.assertEqual([p.name for p in folder.iterdir()], ['candidate-a'])
        original(folder / 'candidate-a')

    def test_atomic_switch_failed_preflight_and_explicit_rollback_preserve_latest_business_bytes(self):
        for release_id in ('candidate-a', 'candidate-b'):
            release.install(self.package(release_id), self.config)
        root = self.config['installation_root']
        self.config['console_state'].mkdir()
        latest = self.config['console_state'] / 'latest-ledger.sqlite'
        latest.write_bytes(b'new reservations and unknown request records')
        def check(path, config):
            return release.verify_directory(path)
        with patch.object(release, 'preflight', side_effect=check):
            release.activate('candidate-a', self.config, stopped=True)
            before = (root / 'current.json').read_bytes()
            with patch.object(release, 'preflight', side_effect=release.ReleaseError('bad candidate')):
                with self.assertRaises(release.ReleaseError):
                    release.activate('candidate-b', self.config, stopped=True)
            self.assertEqual((root / 'current.json').read_bytes(), before)
            release.activate('candidate-b', self.config, stopped=True)
            self.assertEqual(release.selected(self.config).name, 'candidate-b')
            release.activate('candidate-a', self.config, stopped=True)
            self.assertEqual(release.selected(self.config).name, 'candidate-a')
        self.assertEqual(latest.read_bytes(), b'new reservations and unknown request records')

    def test_pointer_replace_failure_preserves_original_and_removes_temporary_pointer(self):
        release.install(self.package(), self.config)
        root = self.config['installation_root']
        with patch.object(release, 'preflight', side_effect=lambda p, c: release.verify_directory(p)):
            release.activate('candidate-a', self.config, stopped=True)
            before = (root / 'current.json').read_bytes()
            with patch.object(release.os, 'replace', side_effect=OSError('controlled replace failure')):
                with self.assertRaises(OSError):
                    release.activate('candidate-a', self.config, stopped=True)
        self.assertEqual((root / 'current.json').read_bytes(), before)
        self.assertEqual(sorted(p.name for p in root.iterdir()), ['current.json', 'releases'])

    def test_mutated_release_and_running_services_do_not_switch_pointer(self):
        release.install(self.package(), self.config)
        with self.assertRaises(release.ReleaseError):
            release.activate('candidate-a', self.config)
        candidate = self.config['installation_root'] / 'releases/candidate-a'
        (candidate / 'extra.txt').write_bytes(b'not in manifest')
        with self.assertRaises(release.ReleaseError):
            release.verify_directory(candidate)
        self.assertFalse((self.config['installation_root'] / 'current.json').exists())

    def test_operation_lock_is_not_removed_or_stolen_by_another_operation(self):
        root = self.config['installation_root']
        with release.operation_lock(root):
            with self.assertRaises(release.ReleaseError):
                release.install(self.package(), self.config)
            self.assertTrue((root / '.operation.lock').exists())
        self.assertFalse((root / '.operation.lock').exists())

    def test_missing_and_overlapping_config_paths_are_rejected_before_any_write(self):
        configuration = {k: str(v) if isinstance(v, Path) else v for k, v in self.config.items()}
        config_file = self.root / 'deployment.json'
        for mutate in (lambda c: c.pop('modeld_config'),
                       lambda c: c.update(console_state=str(self.config['installation_root'] / 'business')),
                       lambda c: c.update(installation_root='relative-path')):
            modified = copy.deepcopy(configuration)
            mutate(modified)
            config_file.write_text(json.dumps(modified), encoding='utf-8')
            with self.assertRaises(release.ReleaseError):
                release.read_config(config_file)
        self.assertFalse(self.config['installation_root'].exists())


if __name__ == '__main__':
    unittest.main()
