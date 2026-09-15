"""hook-post-edit command decision.

This command calls nothing `agent_hooks` owns -- its work is entirely
composing already-moved domain logic from `providers`,
`work`, and `knowledge` -- so it lives in its own
module rather than `commands/agent_hooks.py`: cramming it in there would have
pushed that module's fan-out beyond check 5's cap of 8. This module imported
eight internal modules before the M6 object-registry wiring, not seven. M6
removes three annotation-only imports and adds two object-model
imports, leaving a runtime fan-out of seven because every dependency below is
a complete, self-contained function. An earlier deferral (a
not-yet-available `classify_surfaces`, reached only through conditional,
mid-control-flow calls that could not be expressed as precomputed data) no
longer applies now that both forward dependencies are real functions this
module can call directly.

The wired hook now refreshes one derived tracked file,
`cognition/graph/registry.yaml`, when an edited path is already registered. It
validates object references before writing and remains best-effort. The
`.hydra-framework/hooks/post-merge` hook already performs the same class of
registry refresh after Git changes.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.knowledge.package_checks import PACKAGE_FILE_FAIL_TOKENS, validate_package_root
from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes, knowledge_node_for_path, node_root
from hydra_engine.objects.references import validate_object_references
from hydra_engine.objects.registry import registry_object_entries, write_object_registry
from hydra_engine.providers.reclaim import provider_surface_notice
from hydra_engine.work.placement import tier_placement_notice

PACKAGE_GATE_REPORT_LIMIT = 8


def _reindex_registered_object(root: Path, edited: Path, resolver_paths: ObjectLocations) -> None:
    try:
        entries, errors = registry_object_entries(resolver_paths.object_registry, root)
        if errors:
            return
        edited_rel = edited.relative_to(root).as_posix()
    except (OSError, UnicodeError, ValueError):
        return

    registered_paths = {
        Path(str(entry["path"])).as_posix()
        for entry in entries.values()
        if entry.get("path")
    }
    if edited_rel not in registered_paths:
        return

    try:
        findings = validate_object_references(resolver_paths)
        if findings:
            print(
                f"Hydra object registry refresh skipped after editing {edited_rel}; "
                "run `hydra.py ref check` or `hydra.py ref index` after fixing the findings.",
                file=sys.stderr,
            )
            return
        count = write_object_registry(resolver_paths)
    except (OSError, UnicodeError, ValueError):
        print(
            f"Hydra object registry refresh failed after editing {edited_rel}; "
            "run `hydra.py ref index`.",
            file=sys.stderr,
        )
        return
    if count is None:
        print(
            f"Hydra object registry refresh refused after editing {edited_rel}; "
            "run `hydra.py ref index` again.",
            file=sys.stderr,
        )


def command_hook_post_edit(
    args,
    root: Path,
    providers_paths: ProvidersPaths,
    work_paths: WorkPaths,
    context_compiler_paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    env_owner: str,
    git_email: str,
    command_ids: tuple[str, ...] = (),
    file_fail_tokens: int = PACKAGE_FILE_FAIL_TOKENS,
    chars_per_token: int = 4,
) -> CommandResult:
    raw = sys.stdin.read()
    if not raw:
        return CommandResult(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return CommandResult(0)
    tool_input = data.get("tool_input", data)
    file_value = tool_input.get("file_path") or tool_input.get("path")
    if not file_value:
        return CommandResult(0)
    edited = Path(file_value)
    if not edited.is_absolute():
        edited = root / edited

    _reindex_registered_object(root, edited, resolver_paths)

    # A write into a provider directory is the most common way Hydra gets
    # bypassed: someone adds a skill or subagent where their runtime expects it
    # and the canonical layer never learns about it. Catch it at write time.
    surface_notice = provider_surface_notice(providers_paths, edited)
    if surface_notice:
        for line in surface_notice:
            print(line)
        return CommandResult(0)

    tier_notice = tier_placement_notice(edited, work_paths, env_owner, git_email)
    if tier_notice:
        for line in tier_notice:
            print(line)
        return CommandResult(0)

    if edited.suffix not in {".md", ".dot"}:
        return CommandResult(0)
    if not (context_compiler_paths.hydra / "repo/knowledge/spaces.yaml").is_file():
        return CommandResult(0)
    node = knowledge_node_for_path(edited, discover_knowledge_nodes(context_compiler_paths), context_compiler_paths)
    if node is None:
        return CommandResult(0)
    package_root = node_root(node)
    findings = validate_package_root(
        package_root,
        context_compiler_paths,
        resolver_paths,
        render=args.render,
        command_ids=command_ids,
        file_fail_tokens=file_fail_tokens,
        chars_per_token=chars_per_token,
    )
    if not findings:
        return CommandResult(0)
    edited_rel = str(edited.relative_to(root))
    own, unrelated_count = _split_package_findings(findings, edited_rel)
    if not own:
        if unrelated_count:
            print(
                f"Hydra: {unrelated_count} pre-existing knowledge-node issue(s) in "
                f"{package_root.relative_to(root)}, unrelated to this edit. "
                "Run `hydra.py validate` to see them."
            )
        return CommandResult(0)
    print(f"Hydra knowledge-node gate FAILED for {package_root.relative_to(root)} after editing {edited.relative_to(root)}:", file=sys.stderr)
    for finding in own[:PACKAGE_GATE_REPORT_LIMIT]:
        print(f"- {finding}", file=sys.stderr)
    skipped = len(own) - PACKAGE_GATE_REPORT_LIMIT
    if skipped > 0:
        print(f"- ... and {skipped} more issue(s) caused by this file", file=sys.stderr)
    if unrelated_count:
        print(
            f"({unrelated_count} pre-existing knowledge-node issue(s) elsewhere, unrelated to this edit; "
            "run `hydra.py validate` to see them)",
            file=sys.stderr,
        )
    return CommandResult(2)


def _split_package_findings(findings: list[Finding], edited_rel: str) -> tuple[list[Finding], int]:
    """Split package validation findings into ones this edit caused and a count of the rest.

    A knowledge package is a cross-linked graph, so slice 01 legitimately links
    slice 02 before slice 02 exists: every intermediate write during multi-file
    package authoring is a guaranteed failure against the whole package, and an
    unscoped report repeats the same growing "not finished yet" dump on every
    write. What an author can act on right now is whether the file they just
    touched broke something; the rest is pre-existing and stays a count.

    `finding.path` is a structural match against the edited file. The regex
    over `finding.detail` covers the case a structural match misses: a
    routing-file finding is always attributed to `routing.yaml`, but the text
    itself names the missing or stale target -- which may be the file this
    edit just touched, moved, or deleted.
    """
    pattern = re.compile(rf"(?<![\w./-]){re.escape(edited_rel)}(?![\w./-])")
    own: list[Finding] = []
    unrelated_count = 0
    for finding in findings:
        if finding.path == edited_rel or pattern.search(finding.detail):
            own.append(finding)
        else:
            unrelated_count += 1
    return own, unrelated_count


def register(subparsers) -> None:
    """Add `hook-post-edit`."""
    hook = subparsers.add_parser("hook-post-edit", help="Run package-local gates for edited knowledge-package files")
    hook.add_argument("--render", action="store_true", help="Render DOT diagrams during the hook")
    hook.set_defaults(func=_dispatch_hook_post_edit)


def _dispatch_hook_post_edit(args, ctx) -> int:
    return command_hook_post_edit(
        args,
        ctx.root,
        ctx.providers_paths(),
        ctx.work_paths(),
        ctx.context_compiler_paths(),
        ctx.resolver_paths(),
        ctx.env_owner(),
        ctx.git_email(),
        ctx.command_ids,
        file_fail_tokens=ctx.threshold_value("hydra_engine.knowledge.package_checks.PACKAGE_FILE_FAIL_TOKENS"),
        chars_per_token=ctx.threshold_value("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
    ).exit_code
