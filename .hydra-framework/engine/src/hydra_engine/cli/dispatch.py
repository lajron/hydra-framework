"""Permanent composition root for Hydra CLI dispatch.

`RepoContext`/`main` own root derivation and pass explicit path/context objects
to command modules. Validate/doctor compose their check order through
`checks.validator_registry`; command registration is the only switchboard here.
"""

from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

from hydra_engine.agent_hooks import retry_state
from hydra_engine.agent_hooks.paths import AgentHooksPaths
from hydra_engine.checks import validator_registry
from hydra_engine.checks.aggregation import Check
from hydra_engine.cli import command_metadata
from hydra_engine.cli import parser as cli_parser
from hydra_engine.cli import route_prompt
from hydra_engine.commands import agent_hooks, capability, context, explain_path, hooks, installation, intake, integrate, knowledge, knowledge_bindings, object_moves, private_tier, providers, references, schema, seed, subagents, takeover, telemetry as telemetry_commands, validation, wiki, work
from hydra_engine.config import ConfigError, ConfigPaths, config_advisory_notes, load_effective_config, threshold_default, threshold_value
from hydra_engine.installation.adopt import REQUIRED_PATHS
from hydra_engine.installation.paths import InstallationPaths
from hydra_engine.installation.private_tier import private_tier_report
from hydra_engine.intake.paths import IntakePaths
from hydra_engine.knowledge import search_index
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.objects.discovery import ObjectLocations
from hydra_engine.ports import clock, git as git_port
from hydra_engine.providers import reclaim
from hydra_engine.providers.paths import ProvidersPaths
from hydra_engine.seed import candidate_queue, reflections
from hydra_engine.seed.paths import SeedPaths
from hydra_engine.telemetry import evidence as telemetry_evidence
from hydra_engine.wiki.paths import WikiPaths
from hydra_engine.work import owners, task_records as work_task_records
from hydra_engine.work.owners import HydraOwnerError
from hydra_engine.work.paths import WorkPaths

# Every command module's CLI registration, iterated by `cli.parser.build_parser`
# instead of a per-command switchboard (exempt from check 5's fan-out cap here).
COMMAND_MODULES = (agent_hooks, capability, context, explain_path, hooks, installation, intake, integrate, knowledge, knowledge_bindings, object_moves, private_tier, providers, references, route_prompt, schema, seed, subagents, takeover, telemetry_commands, wiki, work)

# Independent copy, matching `work.paths.WorkPaths`'s own.
PERSONAL_TASKS_REL = "tasks/personal"


@dataclasses.dataclass(frozen=True)
class RepoContext:
    """Explicit repository-root binding, threaded through every command.
    Per-area location dataclasses are methods, not fields -- cheap enough to
    call more than once per dispatch without memoizing."""

    root: Path
    hydra: Path
    local: Path
    project_wiki: Path
    object_registry: Path
    adaptation_ledger: Path
    manifest: dict = dataclasses.field(default_factory=dict)
    module_metadata_entries: tuple = ()
    command_ids: tuple[str, ...] = ()

    @classmethod
    def for_root(cls, root: Path) -> "RepoContext":
        hydra = root / ".hydra-framework"
        return cls(
            root=root,
            hydra=hydra,
            local=root / ".hydra-framework.local",
            project_wiki=root / "project-wiki",
            object_registry=hydra / "cognition/graph/registry.yaml",
            adaptation_ledger=hydra / "evolution/adaptations.md",
        )

    def with_manifest(self, manifest: dict) -> "RepoContext": return dataclasses.replace(self, manifest=manifest)

    def with_module_metadata_entries(self, entries) -> "RepoContext": return dataclasses.replace(self, module_metadata_entries=tuple(entries))

    def env_owner(self) -> str: return os.environ.get("HYDRA_OWNER", "")

    def git_email(self) -> str: return git_port.config_email(self.root)

    def resolver_paths(self) -> ObjectLocations:
        return ObjectLocations(
            root=self.root,
            hydra=self.hydra,
            local=self.local,
            personal_tasks_rel=PERSONAL_TASKS_REL,
            object_registry=self.object_registry,
        )

    def work_paths(self) -> WorkPaths: return WorkPaths(root=self.root, hydra=self.hydra, local=self.local)
    def agent_hooks_paths(self) -> AgentHooksPaths: return AgentHooksPaths(root=self.root, local=self.local)
    def config_paths(self) -> ConfigPaths: return ConfigPaths(root=self.root, hydra=self.hydra, local=self.local)
    def wiki_paths(self) -> WikiPaths: return WikiPaths(root=self.root, project_wiki=self.project_wiki)
    def context_compiler_paths(self) -> ContextCompilerPaths: return ContextCompilerPaths(root=self.root, hydra=self.hydra)
    def providers_paths(self) -> ProvidersPaths: return ProvidersPaths(root=self.root, hydra=self.hydra)

    def threshold_value(self, key: str) -> int:
        return threshold_value(load_effective_config(self.config_paths()), key)

    def threshold_value_or_default(self, key: str) -> int:
        try:
            return self.threshold_value(key)
        except ConfigError:
            return threshold_default(key)

    def seed_paths(self) -> SeedPaths:
        return SeedPaths(root=self.root, hydra=self.hydra, adaptation_ledger=self.adaptation_ledger)

    def installation_paths(self) -> InstallationPaths:
        return InstallationPaths(root=self.root, hydra=self.hydra)

    def intake_paths(self) -> IntakePaths:
        return IntakePaths(root=self.root, hydra=self.hydra)


def _yaml_map(value: object) -> dict:
    # `yaml_map`'s one-line semantics, reimplemented locally rather than
    # importing `documents.yaml_documents` for it alone (already at check 4's
    # in-degree cap of 10 -- matches `installation.adopt`'s own `_as_map`).
    return value if isinstance(value, dict) else {}


def _validate_checks(ctx: RepoContext) -> list[Check]:
    # Order is `checks.validator_registry.VALIDATORS`'s to own and explain.
    return validator_registry.checks_for(ctx)


def _advisory_notes(ctx: RepoContext) -> list[str]:
    today = clock.today()
    t = ctx.threshold_value_or_default
    notes = work_task_records.personal_task_notes(ctx.work_paths(), t("hydra_engine.work.task_records.STALE_TASK_DAYS"))
    notes += reflections.reflection_queue_notes(ctx.hydra / "evolution" / "reflections", ctx.root, today, t("hydra_engine.seed.reflections.STALE_REFLECTION_DAYS"), t("hydra_engine.seed.reflections.REFLECTION_QUEUE_DEPTH_NOTE"))
    notes += candidate_queue.candidate_queue_notes(ctx.hydra / "evolution" / "candidates", ctx.root, today, t("hydra_engine.seed.candidate_queue.STALE_PROPOSED_CANDIDATE_DAYS"))
    notes += telemetry_evidence.telemetry_evidence_notes(ctx.hydra / "repo" / "telemetry" / "packages", ctx.root, ctx.hydra, today, t("hydra_engine.telemetry.evidence.STALE_OPEN_TELEMETRY_EVIDENCE_DAYS"), t("hydra_engine.telemetry.evidence.TELEMETRY_EVIDENCE_QUEUE_DEPTH_NOTE"))
    # Append-only state is
    # never compacted, so these are the only place its growth surfaces.
    notes += retry_state.retry_state_growth_notes(ctx.agent_hooks_paths(), t("hydra_engine.agent_hooks.retry_state.RETRY_STATE_GROWTH_ADVISORY_LINES"))
    notes += search_index.knowledge_events_growth_notes(ctx.local, ctx.root, t("hydra_engine.telemetry.writer.TELEMETRY_EVENTS_GROWTH_ADVISORY_LINES"))
    return notes + config_advisory_notes(ctx.config_paths())


def _dispatch_validate(args, ctx: RepoContext) -> int:
    return validation.command_validate(_validate_checks(ctx), _advisory_notes(ctx)).exit_code


def _dispatch_doctor(args, ctx: RepoContext) -> int:
    try:
        owner = owners.resolve_owner("", ctx.env_owner(), ctx.git_email())
    except HydraOwnerError:
        owner = None
    installation_paths = ctx.installation_paths()
    hooks_relative = installation_paths.hooks_dir().relative_to(ctx.root).as_posix()
    return validation.command_doctor(
        missing_required_paths=[path for path in REQUIRED_PATHS if not (ctx.root / path).exists()],
        tasks=work_task_records.iter_personal_task_files(ctx.work_paths()),
        owner=owner,
        local_exists=ctx.local.exists(),
        private_tier=private_tier_report(ctx.root, ctx.local),
        hooks_installed=installation.hooks_path_matches(ctx.root, hooks_relative),
        knowledge_index_status=search_index.index_status(
            ctx.context_compiler_paths(), ctx.resolver_paths(), ctx.local, ctx.command_ids
        ),
        object_store_status=references.store_status(ctx.resolver_paths()),
        surfaces=reclaim.classify_surfaces(ctx.providers_paths()),
        lineage=_yaml_map(ctx.manifest.get("lineage")),
        checks=_validate_checks(ctx),
        notes=_advisory_notes(ctx),
    ).exit_code


# Not a COMMAND_MODULES member: it introspects that tuple, so it's registered here, like validate/doctor.
def _register_direct_commands(subparsers) -> None:
    subparsers.add_parser("validate", help="Validate Hydra task and adapter basics").set_defaults(func=_dispatch_validate)
    subparsers.add_parser("doctor", help="Check required Hydra paths and run validation").set_defaults(func=_dispatch_doctor)
    metadata = subparsers.add_parser("command-metadata", help="List registered commands with generated arguments and hand-authored side-effect metadata")
    metadata.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    metadata.set_defaults(func=lambda args, ctx: command_metadata.dispatch(args, COMMAND_MODULES))


def main(argv: list[str] | None, ctx: RepoContext, legacy_register=None) -> int:
    def _extra(subparsers) -> None:
        _register_direct_commands(subparsers)
        if legacy_register is not None:
            legacy_register(subparsers)

    parser = cli_parser.build_parser(COMMAND_MODULES, _extra)
    args = parser.parse_args(argv)
    ctx = dataclasses.replace(ctx, command_ids=tuple(entry.id for entry in command_metadata.generate_command_metadata(parser)))
    try:
        return args.func(args, ctx)
    except HydraOwnerError as error:
        print(str(error), file=sys.stderr)
        return 1
