"""The remaining `validate` checks `checks.repo_findings` could not also
hold under check 5's fan-out cap of 8 --
see that module's docstring for why the composition is split in two.
"""

from __future__ import annotations

from hydra_engine.checks.provider_surfaces import provider_surface_findings
from hydra_engine.checks.task_contract_docs import REQUIRED_TASK_SECTIONS
from hydra_engine.knowledge import flat_files, nodes, package_checks
from hydra_engine.providers import reclaim
from hydra_engine.seed import reflections
from hydra_engine.work import task_records


def task_records_check(ctx) -> list:
    findings = []
    for task_path in task_records.iter_personal_task_files(ctx.work_paths()):
        findings.extend(task_records.validate_task_file(task_path, REQUIRED_TASK_SECTIONS, ctx.root))
        findings.extend(task_records.validate_personal_task_file(task_path, ctx.root))
    findings.extend(task_records.duplicate_task_slug_findings(ctx.work_paths()))
    return findings


def provider_surfaces_check(ctx) -> list:
    return provider_surface_findings(reclaim.classify_surfaces(ctx.providers_paths()))


def package_docs_check(ctx) -> list:
    findings = []
    if not (nodes.knowledge_root(ctx.context_compiler_paths()) / "spaces.yaml").is_file():
        return findings
    for node in nodes.discover_knowledge_nodes(ctx.context_compiler_paths()):
        findings.extend(package_checks.validate_package_root(
            node.path.parent,
            ctx.context_compiler_paths(),
            ctx.resolver_paths(),
            render=False,
            command_ids=ctx.command_ids,
            file_fail_tokens=ctx.threshold_value_or_default("hydra_engine.knowledge.package_checks.PACKAGE_FILE_FAIL_TOKENS"),
            chars_per_token=ctx.threshold_value_or_default("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
        ))
    return findings


def flat_knowledge_check(ctx) -> list:
    return flat_files.validate_flat_knowledge_files(ctx.hydra, ctx.root)


def reflection_queue_check(ctx) -> list:
    return reflections.validate_reflection_queue(
        ctx.hydra / "evolution" / "reflections",
        ctx.root,
        fail_tokens=ctx.threshold_value_or_default("hydra_engine.seed.reflections.REFLECTION_PACKET_FAIL_TOKENS"),
        chars_per_token=ctx.threshold_value_or_default("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
    )
