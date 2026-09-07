"""Knowledge v3 node-document validation command."""

from __future__ import annotations

from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import is_relative_to
from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes
from hydra_engine.knowledge.nodes import validate_knowledge_nodes
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


def _under(path: str, roots: set[str]) -> bool:
    return any(path == root or path.startswith(f"{root}/") for root in roots)


def _node_document_findings(roots: list[Path], paths: ContextCompilerPaths) -> list:
    """Node-document findings that concern the selected roots.

    The v2 gate validated each package's `routing.yaml`, so the post-edit hook
    caught a malformed document locally. Reuse the same whole-tree rules the
    full validator applies rather than keeping a second copy of the contract,
    and keep two classes of finding: those belonging to a selected root, and
    those belonging to no node at all, which describe the tree itself and
    would otherwise be filtered away with no gate reporting them.
    """
    if not (paths.hydra / "repo/knowledge/spaces.yaml").is_file():
        return []
    def relative(path: Path) -> str:
        return path.relative_to(paths.root).as_posix() if is_relative_to(path, paths.root) else str(path)

    selected = {relative(root) for root in roots}
    owned = {relative(node.path.parent) for node in discover_knowledge_nodes(paths)}
    return [
        finding for finding in validate_knowledge_nodes(paths)
        if _under(finding.path, selected) or not _under(finding.path, owned)
    ]


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
    findings: list = _node_document_findings(roots, paths)
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
