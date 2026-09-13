"""Per-checkout export lock port.

`fcntl` (POSIX) and `msvcrt` (Windows) are both stdlib, so the lock that
guards `export-adapters`/`profile select` needs no third-party dependency.
The lock **fails closed**: if neither import succeeds, `acquire` raises
`LockUnavailableError` rather than falling back to a no-op, because a no-op
fallback would contradict the guarantee that concurrent exporters cannot
interleave writes and removals.

`LockUnavailableError` subclasses `HydraYamlError` so every existing call
site that already catches `(HydraYamlError, ConfigError)` around export
handles it with no new except clause, matching the same "subclass an
already-caught type" rule the plan applies to profile-resolution errors.
"""

from __future__ import annotations

import contextlib
import time
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None


class LockUnavailableError(HydraYamlError):
    """No platform lock mechanism is importable; refuse to mutate."""


def _try_lock(handle) -> bool:
    if fcntl is not None:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


@contextlib.contextmanager
def acquire(path: Path):
    """Hold the exclusive per-checkout lock at `path` for the block's duration.

    Creates the lock file's parent directory if missing. Raises
    `LockUnavailableError` immediately, before touching the filesystem, when
    neither `fcntl` nor `msvcrt` is available.
    """
    if fcntl is None and msvcrt is None:
        raise LockUnavailableError(
            "no platform lock mechanism (fcntl/msvcrt) is available; refusing to mutate"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+")
    try:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        else:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        handle.close()


@contextlib.contextmanager
def try_acquire(path: Path, timeout: float = 0.0):
    """Try to hold *path* exclusively for at most *timeout* seconds.

    The port keeps its fail-closed platform behavior.  Contention is reported
    as ``LockUnavailableError`` instead of waiting indefinitely as ``acquire``
    does.
    """
    if fcntl is None and msvcrt is None:
        raise LockUnavailableError(
            "no platform lock mechanism (fcntl/msvcrt) is available; refusing to mutate"
        )
    if timeout < 0:
        raise ValueError("timeout must not be negative")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+")
    deadline = time.monotonic() + timeout
    acquired = False
    try:
        while not acquired:
            acquired = _try_lock(handle)
            if acquired:
                break
            if time.monotonic() >= deadline:
                raise LockUnavailableError(f"lock is unavailable: {path}")
            time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        handle.close()
