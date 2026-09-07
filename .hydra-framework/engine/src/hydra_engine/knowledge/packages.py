"""Shared filesystem paths for the context compiler.

Flat-package discovery was intentionally removed when the active runtime
became Knowledge v3-only.  The path bundle remains here to avoid an unrelated
import migration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextCompilerPaths:
    root: Path
    hydra: Path

    def hydra_script(self) -> Path:
        return self.hydra / "scripts/hydra.py"
