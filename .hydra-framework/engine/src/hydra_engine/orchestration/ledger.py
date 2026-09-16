"""Lock-protected local persistence for orchestration state."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from hydra_engine.documents.tokens import read_text, write_text
from hydra_engine.ports import lock as lock_port
from hydra_engine.orchestration import models, schema

T = TypeVar("T")


@dataclass(frozen=True)
class OrchestrationPaths:
    """Explicit repository and private-tier locations for the control plane."""

    root: Path
    hydra: Path
    local: Path

    def ledger_path(self) -> Path:
        return self.local / "orchestration" / "ledger.json"

    def lock_path(self) -> Path:
        return self.local / "locks" / "orchestration.lock"


class LocalLedger:
    """Read and atomically update one private orchestration ledger."""

    def __init__(self, paths: OrchestrationPaths):
        self.paths = paths

    def read(self) -> dict[str, Any]:
        with lock_port.acquire(self.paths.lock_path()):
            return self._load_unlocked()

    def update(self, change: Callable[[dict[str, Any]], T]) -> T:
        """Run a mutation under the checkout lock and publish it atomically."""
        with lock_port.acquire(self.paths.lock_path()):
            data = self._load_unlocked()
            result = change(data)
            try:
                schema.validate_ledger(data)
            except models.LedgerCorruptError:
                raise
            encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
            if len(encoded.encode("utf-8")) > models.ledger_limit_bytes:
                raise models.LedgerError(f"local orchestration ledger exceeds the {models.ledger_limit_bytes}-byte limit")
            write_text(self.paths.ledger_path(), encoded)
            return result

    def _load_unlocked(self) -> dict[str, Any]:
        path = self.paths.ledger_path()
        if not path.exists():
            return models.empty_ledger()
        if not path.is_file():
            raise models.LedgerError(f"local orchestration ledger is not a file: {path}")
        try:
            data = json.loads(read_text(path))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise models.LedgerCorruptError(f"local orchestration ledger cannot be decoded: {path}") from error
        try:
            schema.validate_ledger(data)
        except models.LedgerCorruptError:
            raise
        return data
