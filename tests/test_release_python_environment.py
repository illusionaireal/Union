"""A configured virtual environment must remain the runtime selected by installation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

from scripts.release_package import read_config


class ReleasePythonEnvironmentTests(unittest.TestCase):
    def test_configured_venv_keeps_its_prefix_under_isolated_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = root / 'runtime'
            venv.EnvBuilder(with_pip=False, symlinks=os.name != 'nt').create(environment)
            executable = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            private = root / 'private'
            private.mkdir()
            modeld = private / 'modeld.json'
            modeld.write_text('{}')
            config_file = root / 'deployment.json'
            config_file.write_text(json.dumps({
                'installation_root': str(root / 'code'), 'console_state': str(root / 'business'),
                'modeld_config': str(modeld), 'python': str(executable),
                'bun': sys.executable, 'console_port': 18766,
            }))
            configured = read_config(config_file)
            actual = subprocess.check_output([str(configured['python']), '-I', '-B', '-c',
                                              'import sys; print(sys.prefix)'], text=True).strip()
            self.assertEqual(Path(actual).resolve(), environment.resolve(),
                             'Resolving the executable symlink silently selects the system interpreter')
