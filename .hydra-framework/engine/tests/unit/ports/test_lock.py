"""Mirror test for `hydra_engine.ports.lock`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents.tokens import HydraYamlError  # noqa: E402
from hydra_engine.ports import lock  # noqa: E402


def _lock_path() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ports-lock-"))
    return root / "locks" / "export.lock"


class AcquireTests(unittest.TestCase):
    def test_acquire_creates_missing_parent_and_releases_on_exit(self):
        path = _lock_path()
        with lock.acquire(path):
            self.assertTrue(path.exists())
        with lock.acquire(path):
            pass

    def test_lock_unavailable_error_subclasses_hydra_yaml_error(self):
        self.assertTrue(issubclass(lock.LockUnavailableError, HydraYamlError))

    def test_fails_closed_when_no_platform_mechanism_is_available(self):
        path = _lock_path()
        with mock.patch.object(lock, "fcntl", None), mock.patch.object(lock, "msvcrt", None):
            with self.assertRaises(lock.LockUnavailableError):
                with lock.acquire(path):
                    pass
        self.assertFalse(path.exists())

    def test_body_exceptions_still_release_the_lock(self):
        path = _lock_path()
        with self.assertRaises(RuntimeError):
            with lock.acquire(path):
                raise RuntimeError("boom")
        with lock.acquire(path):
            pass


if __name__ == "__main__":
    unittest.main()
