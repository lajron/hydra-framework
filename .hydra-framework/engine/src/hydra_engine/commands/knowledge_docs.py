"""Knowledge v3 node-document validation command."""

from __future__ import annotations

from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import is_relative_to
from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes
from hydra_engine.knowledge import package_checks
from hydra_engine.knowledge.packages import ContextCompilerPaths


def node_roots_from_args(args, paths: ContextCompilerPaths) -> list[Path]:
    if getattr(args, "path", None):
        return [Path(args.path).resolve()]
    selector = getattr(args, "node", None) or getattr(args, "package", None)
    if not (paths.hydra / "repo/knowledge/spaces.yaml").is_file():
        return []
    nodes = discover_knowledge_nodes(paths)
    if selector:
        return [
            node.path.parent for node in nodes
            if node.logical_id == selector or node.logical_id.rsplit("/", 1)[-1] == selector
        ]
    return [node.path.parent for node in nodes]


def validate_node_docs(
    args,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    command_ids: tuple[str, ...] = (),
    file_fail_tokens: int = package_checks.PACKAGE_FILE_FAIL_TOKENS,
    chars_per_token: int = package_checks.APPROX_CHARS_PER_TOKEN,
) -> CommandResult:
    roots = node_roots_from_args(args, paths)
    if not roots:
        print("Hydra Knowledge v3 docs: no knowledge nodes found")
        return CommandResult(0)
    findings: list = []
    for root in roots:
        shown = root.relative_to(paths.root) if is_relative_to(root, paths.root) else root
        print(f"Hydra Knowledge v3 docs: {shown}")
        findings.extend(package_checks.validate_package_root(
            root, paths, resolver_paths, render=args.render, command_ids=command_ids,
            file_fail_tokens=file_fail_tokens, chars_per_token=chars_per_token,
        ))
    if findings:
        print("Hydra Knowledge v3 docs: failed")
        for finding in findings:
            print(f"- {finding}")
        return CommandResult(1)
    print("Hydra Knowledge v3 docs: ok")
    return CommandResult(0)
