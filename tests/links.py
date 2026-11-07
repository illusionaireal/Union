"""Shared preparation of directory links for boundary tests (U-078).

Linux creates a symlink. Windows first tries a symlink (available with Developer
Mode) and falls back to a directory junction, which needs no privilege. A host
that cannot provide either raises LinkUnavailable, so a preparation limit is
never mistaken for a product behaviour failure and `cmd` is never called on
POSIX.
"""
import subprocess
import sys
from pathlib import Path


class LinkUnavailable(RuntimeError):
    """The host cannot prepare the link this test needs; skip, do not fail."""


def _windows_junction(target, link):
    completed = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                               capture_output=True, text=True)
    if completed.returncode != 0 or not Path(link).exists():
        detail = (completed.stderr or completed.stdout or "").strip()
        raise LinkUnavailable("host cannot create a directory junction: " + detail)
    return Path(link)


def directory_link(target, link):
    """Create a directory link at `link` pointing to `target`."""
    target, link = Path(target), Path(link)
    if sys.platform.startswith("win"):
        try:
            link.symlink_to(target, target_is_directory=True)
            return link
        except (OSError, NotImplementedError):
            pass
        return _windows_junction(target, link)
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        raise LinkUnavailable("host cannot create a directory symlink: " + str(error)) from error
    return link


def skip_reason(error):
    """Short reason text for skipTest when preparation is unavailable."""
    return "host cannot prepare a directory link: " + str(error)
