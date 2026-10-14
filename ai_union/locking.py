"""Non-blocking local process locks; the same lock protects CLI and web commands."""
import os
from contextlib import contextmanager

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def lock(file):
    if os.name == "nt":
        file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def unlock(file):
    if os.name == "nt":
        file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)


@contextmanager
def file_lock(path):
    with path.open("a+b") as file:
        lock(file)
        try:
            yield
        finally:
            unlock(file)


def held(path):
    """Probe an existing lock without creating or writing any file."""
    try:
        with path.open("rb") as file:
            try:
                lock(file)
            except OSError:
                return True
            unlock(file)
    except FileNotFoundError:
        pass
    return False
