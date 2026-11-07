"""U-078: the shared directory-link preparation must work on Linux and Windows.

Windows without symlink privilege is a host limitation, not a product behaviour
failure, so it must be reported distinctly (LinkUnavailable) instead of leaking
WinError 1314 or calling `cmd` on Linux.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import links


class DirectoryLinkTests(unittest.TestCase):
    def test_linux_uses_a_symlink_and_never_calls_windows_cmd(self):
        target = Path("target")
        link = Path("link")
        calls = {}

        def fake_symlink(self, to, target_is_directory=False):
            calls["to"] = to
            calls["directory"] = target_is_directory

        with patch.object(links.sys, "platform", "linux"), \
                patch.object(Path, "symlink_to", fake_symlink), \
                patch.object(links.subprocess, "run") as run:
            links.directory_link(target, link)
        self.assertEqual(calls, {"to": target, "directory": True})
        run.assert_not_called()

    def test_windows_falls_back_to_a_junction_when_symlink_is_unavailable(self):
        target = Path("target")
        link = Path("link")
        commands = []

        def refused(self, to, target_is_directory=False):
            raise OSError(1314, "client does not hold the required privilege")

        class Completed:
            returncode = 0
            stdout = "Junction created"
            stderr = ""

        def fake_run(argv, **kwargs):
            commands.append(argv)
            return Completed()

        with patch.object(links.sys, "platform", "win32"), \
                patch.object(Path, "symlink_to", refused), \
                patch.object(links.subprocess, "run", fake_run), \
                patch.object(Path, "exists", lambda self: True):
            links.directory_link(target, link)
        self.assertEqual(commands[0][:3], ["cmd", "/c", "mklink"])
        self.assertIn("/J", commands[0])

    def test_an_unsupported_host_reports_a_preparation_limit(self):
        def refused(self, to, target_is_directory=False):
            raise OSError(1314, "client does not hold the required privilege")

        with patch.object(links.sys, "platform", "win32"), \
                patch.object(Path, "symlink_to", refused), \
                patch.object(links.subprocess, "run") as run, \
                patch.object(Path, "exists", lambda self: False):
            run.return_value.returncode = 1
            run.return_value.stdout = ""
            run.return_value.stderr = "The client does not hold the required privilege"
            with self.assertRaises(links.LinkUnavailable) as caught:
                links.directory_link(Path("target"), Path("link"))
        self.assertIn("privilege", str(caught.exception))

    def test_posix_symlink_failure_is_also_a_preparation_limit(self):
        def refused(self, to, target_is_directory=False):
            raise OSError(1, "operation not permitted")

        with patch.object(links.sys, "platform", "linux"), patch.object(Path, "symlink_to", refused):
            with self.assertRaises(links.LinkUnavailable):
                links.directory_link(Path("target"), Path("link"))


if __name__ == "__main__":
    unittest.main()
