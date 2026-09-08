#!/usr/bin/env python3
"""Hydra framework helper: thin CLI shim over `hydra_engine`, exempted by architecture check 8 for root-derivation and `command_selftest`'s own `__file__` read."""

from __future__ import annotations

import sys
from pathlib import Path

_HYDRA = Path(__file__).resolve().parents[1]
for _p in (_HYDRA, _HYDRA / "engine" / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from hydra_engine.checks import module_metadata as module_metadata_engine  # noqa: E402
from hydra_engine.cli import dispatch as cli_dispatch  # noqa: E402
from hydra_engine.documents import yaml_documents as yaml_documents_engine  # noqa: E402

RepoContext = cli_dispatch.RepoContext

def _module_metadata_entries(ctx: RepoContext) -> list[module_metadata_engine.ModuleMetadataEntry]:
    entries: list[module_metadata_engine.ModuleMetadataEntry] = []
    for subdir, body_name, required in module_metadata_engine.MODULE_METADATA_CHECKS:
        subdir_root = ctx.hydra / subdir
        if not subdir_root.is_dir():
            continue
        for module_dir in sorted(p for p in subdir_root.glob("*") if p.is_dir() and (p / body_name).exists()):
            metadata = module_dir / "metadata.yaml"
            data = parse_error = None
            if metadata.exists():
                try:
                    data = yaml_documents_engine.parse_yaml(metadata, ctx.root)
                except yaml_documents_engine.HydraYamlError as error:
                    parse_error = str(error)
            entries.append(module_metadata_engine.ModuleMetadataEntry(
                module_dir=module_dir, metadata_path=metadata, required=required,
                is_skill=subdir == "capabilities/skills", data=data, parse_error=parse_error,
            ))
    return entries

def command_selftest(args) -> int:
    import unittest
    tests_dir = _HYDRA / "engine" / "tests"
    loader = unittest.TestLoader()
    suite = loader.discover(str(tests_dir), pattern="test_*.py", top_level_dir=str(tests_dir))
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    return 0 if runner.run(suite).wasSuccessful() else 1

def _register_selftest(subparsers) -> None:
    selftest = subparsers.add_parser("selftest", help="Run the bundled unit tests for this script")
    selftest.add_argument("--verbose", action="store_true", help="Show individual test names")
    selftest.set_defaults(func=lambda args, ctx: command_selftest(args))

def main(argv: list[str] | None = None, ctx: RepoContext | None = None) -> int:
    run_ctx = ctx or RepoContext.for_root(_HYDRA.parent)
    manifest = yaml_documents_engine.parse_yaml(run_ctx.hydra / "manifest.yaml", run_ctx.root)
    run_ctx = run_ctx.with_manifest(manifest).with_module_metadata_entries(_module_metadata_entries(run_ctx))
    return cli_dispatch.main(argv, run_ctx, _register_selftest)

if __name__ == "__main__":
    raise SystemExit(main())
