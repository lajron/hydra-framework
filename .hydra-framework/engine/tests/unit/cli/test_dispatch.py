"""Unit tests for hydra_engine.cli.dispatch."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hydra_engine.cli import dispatch
from hydra_engine import thresholds
from hydra_engine.work.owners import HydraOwnerError


class RepoContextTests(unittest.TestCase):
    def test_for_root_derives_every_path(self) -> None:
        root = Path("/tmp/example-repo")
        ctx = dispatch.RepoContext.for_root(root)
        self.assertEqual(ctx.root, root)
        self.assertEqual(ctx.hydra, root / ".hydra-framework")
        self.assertEqual(ctx.local, root / ".hydra-framework.local")
        self.assertEqual(ctx.project_wiki, root / "project-wiki")
        self.assertEqual(ctx.object_registry, ctx.hydra / "cognition/graph/registry.yaml")
        self.assertEqual(ctx.adaptation_ledger, ctx.hydra / "evolution/adaptations.md")
        self.assertEqual(ctx.manifest, {})
        self.assertEqual(ctx.command_ids, ())

    def test_with_manifest_replaces_only_that_field_and_leaves_the_original_alone(self) -> None:
        ctx = dispatch.RepoContext.for_root(Path("/tmp/example-repo"))
        updated = ctx.with_manifest({"seed_version": "1"})
        self.assertEqual(updated.manifest, {"seed_version": "1"})
        self.assertEqual(updated.root, ctx.root)
        self.assertEqual(ctx.manifest, {})

    def test_per_area_paths_share_the_context_root(self) -> None:
        root = Path("/tmp/example-repo")
        ctx = dispatch.RepoContext.for_root(root)
        self.assertEqual(ctx.work_paths().root, root)
        self.assertEqual(ctx.agent_hooks_paths().root, root)
        self.assertEqual(ctx.wiki_paths().project_wiki, ctx.project_wiki)
        self.assertEqual(ctx.context_compiler_paths().hydra, ctx.hydra)
        self.assertEqual(ctx.providers_paths().hydra, ctx.hydra)
        self.assertEqual(ctx.seed_paths().adaptation_ledger, ctx.adaptation_ledger)
        self.assertEqual(ctx.installation_paths().root, root)
        self.assertEqual(ctx.intake_paths().root, root)
        self.assertEqual(ctx.resolver_paths().object_registry, ctx.object_registry)

    def test_env_owner_reads_the_hydra_owner_variable(self) -> None:
        ctx = dispatch.RepoContext.for_root(Path("/tmp/example-repo"))
        old = os.environ.get("HYDRA_OWNER")
        os.environ["HYDRA_OWNER"] = "reed"
        try:
            self.assertEqual(ctx.env_owner(), "reed")
        finally:
            if old is None:
                os.environ.pop("HYDRA_OWNER", None)
            else:
                os.environ["HYDRA_OWNER"] = old

    def test_with_module_metadata_entries_replaces_only_that_field(self) -> None:
        ctx = dispatch.RepoContext.for_root(Path("/tmp/example-repo"))
        updated = ctx.with_module_metadata_entries(["a", "b"])
        self.assertEqual(updated.module_metadata_entries, ("a", "b"))
        self.assertEqual(ctx.module_metadata_entries, ())
        self.assertEqual(updated.root, ctx.root)


def _real_ctx(**threshold_overrides: int) -> dispatch.RepoContext:
    root = Path(tempfile.mkdtemp(prefix="dispatch-test-"))
    hydra = root / ".hydra-framework"
    for provider in ("claude", "codex"):
        capability_map = hydra / f"adapters/providers/{provider}/capability-map.yaml"
        capability_map.parent.mkdir(parents=True)
        capability_map.write_text(
            f"schema: hydra-framework.capability-map.v1\nprovider: {provider}\nverified: fixture\ncertainty: fixture\n"
            "delegation_controls:\n"
            "  generated_agent_policy: supported\n"
            "  generic_subagent_start_context: advisory\n"
            "  effort_class_capping: supported\n"
            "  max_active_workers: advisory\n"
            "  max_depth: advisory\n",
            encoding="utf-8",
        )
    config_root = hydra / "config"
    config_root.mkdir(parents=True)
    config_root.joinpath("engine-policy.yaml").write_text(_engine_policy(**threshold_overrides), encoding="utf-8")
    config_root.joinpath("delegation-policy.yaml").write_text(_delegation_policy(), encoding="utf-8")
    caller_evidence = hydra / "validation/capability-callers.yaml"
    caller_evidence.parent.mkdir(parents=True)
    caller_evidence.write_text(
        "\n".join([
            "schema: hydra-framework.capability-callers.v1",
            "mechanisms:",
            "  fixture:",
            "    classification: manual",
            "    implementation:",
            "      .hydra-framework/validation/capability-callers.yaml:",
            "        - fixture",
            "    callers:",
            "      .hydra-framework/validation/capability-callers.yaml:",
            "        - manual",
            "",
        ]),
        encoding="utf-8",
    )
    shape = hydra / "repo/knowledge/state-tiers.md"
    shape.parent.mkdir(parents=True)
    shape.write_text(_private_tier_shape(), encoding="utf-8")
    profiles = hydra / "capabilities/profiles.yaml"
    profiles.parent.mkdir(parents=True, exist_ok=True)
    profiles.write_text(
        "schema: hydra-framework.capability-profiles.v1\nbaseline_tags: []\ndefault_profile: full\nprofiles: {}\n",
        encoding="utf-8",
    )
    return dispatch.RepoContext.for_root(root)


def _engine_policy(**overrides: int) -> str:
    lines = ["schema: hydra-framework.engine-policy.v1", "thresholds:"]
    for entry in thresholds.THRESHOLDS:
        if entry.classification == thresholds.TEAM_TUNABLE_POLICY:
            lines.append(f"  {entry.key}: {overrides.get(entry.key, entry.value)}")
    return "\n".join(lines) + "\n"


def _delegation_policy() -> str:
    return (
        "schema: hydra-framework.delegation-policy.v1\n"
        "enabled: true\nmax_active_workers: 2\nmax_depth: 1\n"
        "allowed_reasons:\n  - inspection\n"
        "role_defaults:\n  allowed_capability_classes:\n    - fast-default\n  fallback_capability_class: fast-default\n  effort_ceiling: max\n"
        "roles: {}\n"
    )


def _private_tier_shape() -> str:
    paths = [
        "notes", "intake/raw", "intake/extracted", "intake/triage",
        "monitoring", "index", "logs", "baseline", "tasks/retired",
        "migrations", "evolution/experiments", "scratch", "plans",
        "research", "prompts", "diagrams", "source-material", "tickets",
        "bug-reports", "developer", "machine", "repo-overrides", "secrets",
        "locks", "capabilities",
    ]
    rows = "\n".join(f"| `{path}/` | fixture | fixture |" for path in paths)
    return f"""---
title: State Tiers
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources: []
---
# State Tiers

{rows}
"""


class ValidateAndDoctorCompositionTests(unittest.TestCase):
    """Genuinely new step-14 composition, previously `scripts/hydra.py`'s own
    `validate_checks()`/`command_doctor` wrapper."""

    def test_validate_checks_composes_repo_and_package_task_findings(self) -> None:
        checks = dispatch._validate_checks(_real_ctx())
        self.assertEqual(len(checks), 19)
        for check in checks:
            self.assertEqual(check(), [])

    def test_dispatch_validate_prints_ok_on_a_clean_tree(self) -> None:
        ctx = _real_ctx()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exit_code = dispatch._dispatch_validate(None, ctx)
        self.assertEqual(exit_code, 0)
        self.assertIn("Hydra validate: ok", out.getvalue())

    def test_threshold_value_reads_effective_config(self) -> None:
        ctx = _real_ctx(**{"hydra_engine.knowledge.context_packets.DEFAULT_CONTEXT_BUDGET": 7})
        self.assertEqual(ctx.threshold_value("hydra_engine.knowledge.context_packets.DEFAULT_CONTEXT_BUDGET"), 7)

    def test_advisory_notes_use_configured_task_staleness(self) -> None:
        ctx = _real_ctx(**{"hydra_engine.work.task_records.STALE_TASK_DAYS": 2})
        task = ctx.work_paths().owner_task_dir("dana") / "2026-08-20-example.md"
        task.parent.mkdir(parents=True)
        task.write_text(
            "# Task: example\n\n"
            "Status: active\nOwner: dana\nUpdated: 2026-08-20\n\n"
            "## Goal\n\nDo work.\n\n"
            "## Readiness\n\n- Status: ready\n- Blockers and assumptions: none\n\n"
            "## Step State\n\n- Active step: doing work\n",
            encoding="utf-8",
        )
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-08-24"):
            notes = dispatch._advisory_notes(ctx)
        self.assertTrue(any("not updated since 2026-08-20" in note for note in notes))

    def test_dispatch_doctor_reports_missing_required_paths(self) -> None:
        ctx = _real_ctx()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exit_code = dispatch._dispatch_doctor(None, ctx)
        self.assertEqual(exit_code, 1)
        self.assertIn("Hydra doctor: missing required paths", out.getvalue())

    def test_dispatch_doctor_passes_cache_lifecycle_status(self) -> None:
        ctx = _real_ctx()
        result = mock.Mock(exit_code=0)
        with (
            mock.patch.object(dispatch.installation, "hooks_path_matches", return_value=True) as hooks,
            mock.patch.object(dispatch.search_index, "index_status", return_value="fresh") as knowledge,
            mock.patch.object(dispatch.references, "store_status", return_value="stale") as store,
            mock.patch.object(dispatch.validation, "command_doctor", return_value=result) as doctor,
        ):
            exit_code = dispatch._dispatch_doctor(None, ctx)

        self.assertEqual(exit_code, 0)
        hooks.assert_called_once_with(ctx.root, ".hydra-framework/hooks")
        knowledge.assert_called_once_with(ctx.context_compiler_paths(), ctx.resolver_paths(), ctx.local, ctx.command_ids)
        store.assert_called_once_with(ctx.resolver_paths())
        kwargs = doctor.call_args.kwargs
        self.assertTrue(kwargs["hooks_installed"])
        self.assertEqual(kwargs["knowledge_index_status"], "fresh")
        self.assertEqual(kwargs["object_store_status"], "stale")

    def test_command_metadata_dispatches_over_the_real_command_modules(self) -> None:
        ctx = dispatch.RepoContext.for_root(Path("/tmp/example-repo"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exit_code = dispatch.main(["command-metadata", "--json"], ctx)
        self.assertEqual(exit_code, 0)
        rows = {row["id"]: row for row in json.loads(out.getvalue())}
        self.assertIn("side_effects", rows["task complete"])
        self.assertNotIn("side_effects", rows["board"])


class MainDispatchTests(unittest.TestCase):
    def test_main_calls_the_parsed_commands_func_with_ctx(self) -> None:
        calls = []

        class _StubModule:
            @staticmethod
            def register(subparsers):
                stub = subparsers.add_parser("stub")
                stub.set_defaults(func=lambda args, ctx: calls.append(ctx) or 0)

        ctx = dispatch.RepoContext.for_root(Path("/tmp/example-repo"))
        original = dispatch.COMMAND_MODULES
        dispatch.COMMAND_MODULES = (_StubModule,)
        try:
            exit_code = dispatch.main(["stub"], ctx)
        finally:
            dispatch.COMMAND_MODULES = original
        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0].root, ctx.root)
        self.assertIn("stub", calls[0].command_ids)

    def test_main_reports_a_hydra_owner_error_on_stderr(self) -> None:
        class _StubModule:
            @staticmethod
            def register(subparsers):
                stub = subparsers.add_parser("stub")

                def _raise(args, ctx):
                    raise HydraOwnerError("no owner resolvable")

                stub.set_defaults(func=_raise)

        ctx = dispatch.RepoContext.for_root(Path("/tmp/example-repo"))
        original = dispatch.COMMAND_MODULES
        dispatch.COMMAND_MODULES = (_StubModule,)
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                exit_code = dispatch.main(["stub"], ctx)
        finally:
            dispatch.COMMAND_MODULES = original
        self.assertEqual(exit_code, 1)
        self.assertIn("no owner resolvable", stderr.getvalue())

    def test_main_passes_the_extra_hook_through_to_the_parser(self) -> None:
        seen = []

        def _legacy_register(subparsers):
            legacy = subparsers.add_parser("legacy")
            legacy.set_defaults(func=lambda args, ctx: seen.append(ctx) or 0)

        ctx = dispatch.RepoContext.for_root(Path("/tmp/example-repo"))
        exit_code = dispatch.main(["legacy"], ctx, _legacy_register)
        self.assertEqual(exit_code, 0)
        self.assertEqual(seen[0].root, ctx.root)
        self.assertIn("legacy", seen[0].command_ids)


if __name__ == "__main__":
    unittest.main()
