"""knowledge command decisions.

`resolver_paths: ObjectLocations` in `command_validate_package_docs` is a
bare forward-reference type hint, not a real import, matching
`package_checks.validate_package_root`'s own parameter of the same name and
type -- this module never constructs or introspects one either.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.commands.knowledge_fingerprint import command_knowledge_fingerprint
from hydra_engine.documents.tokens import is_relative_to
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN, stale_unit_source_report
from hydra_engine.knowledge import search_index
from hydra_engine.knowledge.package_checks import PACKAGE_FILE_FAIL_TOKENS, validate_package_root
from hydra_engine.knowledge.nodes import discover_knowledge_nodes
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.knowledge.surfaces import measure_context_surfaces


def package_roots_from_args(args, paths: ContextCompilerPaths) -> list[Path]:
    if getattr(args, "path", None):
        return [Path(args.path).resolve()]
    selector = getattr(args, "node", None) or getattr(args, "package", None)
    if not (paths.hydra / "repo/knowledge/spaces.yaml").is_file():
        return []
    nodes = discover_knowledge_nodes(paths)
    if selector:
        matches = [node.path.parent for node in nodes if node.logical_id == selector or node.logical_id.rsplit("/", 1)[-1] == selector]
        return matches
    return [node.path.parent for node in nodes]


def print_context_surface_report(rows: list[dict[str, int | str]], totals: dict[str, int]) -> None:
    print("Hydra context surface estimate")
    print("Approximation: 1 token ~= 4 characters. Use provider telemetry for billing-grade numbers.")
    print("Category          Tokens   Lines    Chars  Path")
    print("----------------  ------  ------  -------  ----")
    for row in rows:
        print("{:<16}  {:>6}  {:>6}  {:>7}  {}".format(row["category"], row["approx_tokens"], row["lines"], row["chars"], row["path"]))
    print("----------------  ------  ------  -------  ----")
    print("{:<16}  {:>6}  {:>6}  {:>7}".format("TOTAL", totals["approx_tokens"], totals["lines"], totals["chars"]))


def command_measure_context(
    args,
    paths: ContextCompilerPaths,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> CommandResult:
    rows, totals = measure_context_surfaces(paths, args.include_generated_skills, args.path, chars_per_token)

    if args.json:
        print(json.dumps({"files": rows, "totals": totals}, indent=2))
    else:
        print_context_surface_report(rows, totals)

    if args.fail_over is not None and totals["approx_tokens"] > args.fail_over:
        print(f"Hydra context surface exceeds budget: {totals['approx_tokens']} > {args.fail_over}", file=sys.stderr)
        return CommandResult(2)
    return CommandResult(0)


def command_validate_package_docs(
    args,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    command_ids: tuple[str, ...] = (),
    file_fail_tokens: int = PACKAGE_FILE_FAIL_TOKENS,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> CommandResult:
    roots = package_roots_from_args(args, paths)
    if not roots:
        print("Hydra Knowledge v3 docs: no knowledge nodes found")
        return CommandResult(0)

    errors: list = []
    for root in roots:
        shown = root.relative_to(paths.root) if is_relative_to(root, paths.root) else root
        print(f"Hydra Knowledge v3 docs: {shown}")
        errors.extend(validate_package_root(
            root,
            paths,
            resolver_paths,
            render=args.render,
            command_ids=command_ids,
            file_fail_tokens=file_fail_tokens,
            chars_per_token=chars_per_token,
        ))

    if errors:
        print("Hydra Knowledge v3 docs: failed")
        for error in errors:
            print(f"- {error}")
        return CommandResult(1)
    print("Hydra Knowledge v3 docs: ok")
    return CommandResult(0)


def _budgeted_results(
    results: list[search_index.SearchResult],
    budget: int,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
    preview_chars: int = search_index.DEFAULT_PREVIEW_CHARS,
) -> list[search_index.SearchResult]:
    selected: list[search_index.SearchResult] = []
    total = 0
    for result in results:
        tokens = result.approx_token_count(chars_per_token, preview_chars)
        if selected and total + tokens > max(budget, 0):
            break
        selected.append(result)
        total += tokens
    return selected


def command_hook_reindex_knowledge(args, paths: ContextCompilerPaths, resolver_paths: ObjectLocations, local: Path, command_ids: tuple[str, ...]) -> CommandResult:
    db_path = search_index.default_db_path(local)
    if args.if_exists and not db_path.exists():
        return CommandResult(0)
    count, features = search_index.build_index(paths, resolver_paths, local, command_ids)
    mode = "FTS5"
    if not features.fts5:
        mode = "substring fallback"
    elif features.trigram:
        mode = "FTS5 trigram"
    print(f"Hydra knowledge index: {count} documents indexed at {db_path.relative_to(paths.root)} ({mode})")
    return CommandResult(0)


def command_knowledge_search(
    args,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    local: Path,
    command_ids: tuple[str, ...],
    default_budget: int = search_index.DEFAULT_BUDGET,
    default_limit: int = search_index.DEFAULT_RESULT_LIMIT,
    preview_chars: int = search_index.DEFAULT_PREVIEW_CHARS,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> CommandResult:
    search_index.record_command_usage(local, "knowledge-search")
    budget = args.budget if args.budget is not None else default_budget
    limit = args.limit if args.limit is not None else default_limit
    results, features, source = search_index.search(
        args.text, paths=paths, resolver_paths=resolver_paths, local=local,
        command_ids=command_ids, path_refs=tuple(args.path or ()), limit=max(limit, 1),
    )
    if not results:
        print("no results")
        return CommandResult(0)
    selected = _budgeted_results(results, budget, chars_per_token, preview_chars)
    for position, result in enumerate(selected, start=1):
        doc = result.document
        tokens = result.approx_token_count(chars_per_token, preview_chars)
        print(f"{position:>2}. [{result.channel:<10}] {tokens:>5} tok  {result.citation() or doc.title}")
        if doc.hydra_id:
            print(f"    {doc.hydra_id}  <{doc.kind}>")
        elif doc.kind:
            print(f"    {doc.title}  <{doc.kind}>")
        snippet = result.snippet_text(preview_chars)
        print("    " + snippet.replace("\n", "\n    "))
        print()
    total = sum(result.approx_token_count(chars_per_token, preview_chars) for result in selected)
    note = f"{total} approx tokens across {len(selected)} results, budget {max(budget, 0)}"
    if len(results) > len(selected):
        note += f"; {len(results) - len(selected)} lower-ranked result(s) omitted"
    capability = "fts5-trigram" if features.fts5 and features.trigram else "fts5" if features.fts5 else "substring"
    print(f"budget note: {note}; source={source}; lexical={capability}", file=sys.stderr)
    return CommandResult(0)


def command_delegation_brief(
    args,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    local: Path,
    command_ids: tuple[str, ...],
    default_limit: int = search_index.DEFAULT_RESULT_LIMIT,
    preview_chars: int = search_index.DEFAULT_PREVIEW_CHARS,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> CommandResult:
    search_index.record_command_usage(local, "delegation-brief")
    limit = args.limit if args.limit is not None else default_limit
    results, _features, _source = search_index.search(
        args.text, paths=paths, resolver_paths=resolver_paths, local=local,
        command_ids=command_ids, path_refs=tuple(args.path or ()), limit=max(limit, 1),
    )
    if not results:
        print(f"Hydra delegation-brief: no results for {args.text!r}; widen the query or use route-prompt.")
        return CommandResult(0)
    selected = _budgeted_results(results, args.budget, chars_per_token, preview_chars)
    total = sum(result.approx_token_count(chars_per_token, preview_chars) for result in selected)
    print(f"Task: {args.text}")
    print(f"Search query used: {args.text!r} (knowledge-search, deterministic lexical)")
    print("")
    print(f"Read first, {len(selected)} target{'s' if len(selected) != 1 else ''}, {total} approx tokens:")
    for position, result in enumerate(selected, start=1):
        doc = result.document
        tokens = result.approx_token_count(chars_per_token, preview_chars)
        print(f"{position:>2}. [{result.channel:<10}] {tokens:>5} tok  {result.citation() or doc.title}")
        if doc.hydra_id:
            print(f"    {doc.hydra_id}  <{doc.kind}>")
    print("")
    print(f"Read budget: {max(args.budget, 0)} approx tokens ({total} already spent on the targets above).")
    if len(results) > len(selected):
        print(f"{len(results) - len(selected)} lower-ranked hit(s) omitted; widen --budget or run `knowledge-search` directly.")
    print("")
    print("Stop rules:")
    print("- Read the targets above, in rank order, before any other exploration.")
    print("- If they answer the task, stop there rather than widening scope.")
    print("- If they miss, say what is missing.")
    print("")
    print("Return: verified facts with file citations, not a restatement of the task.")
    return CommandResult(0)


def command_knowledge_stale(_args, paths: ContextCompilerPaths) -> CommandResult:
    checked_units, rows = stale_unit_source_report(paths)
    print("Hydra stale knowledge sources")
    print(f"Checked units: {checked_units}")
    if not rows:
        print("- none")
        return CommandResult(0)
    for row in rows:
        sources = ", ".join(str(source) for source in row["stale_sources"])
        print(f"- {row['hydra_id']} ({row['node']}, {row['path']}): {sources} committed after checked_on")
    return CommandResult(0)


def register(subparsers) -> None:
    """Add `measure-context` and `validate-package-docs`. `context-pack` was
    removed with context packs; `validate-package-docs` now validates a
    package's `units/` directory instead (`knowledge.package_checks.validate_units_dir`)."""
    measure = subparsers.add_parser("measure-context", help="Estimate token pressure from Hydra prompt and adapter surfaces")
    measure.add_argument("--path", action="append", default=[], help="Additional file or directory to include")
    measure.add_argument("--include-generated-skills", action="store_true", help="Include generated provider skill wrapper bodies")
    measure.add_argument("--fail-over", type=int, help="Exit nonzero when estimated total tokens exceed this budget")
    measure.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    measure.set_defaults(func=_dispatch_measure_context)

    package_docs = subparsers.add_parser("validate-package-docs", help="Validate Knowledge v3 node Markdown links and units")
    package_docs.add_argument("--node", help="Knowledge node id or unambiguous leaf slug")
    package_docs.add_argument("--package", help="Deprecated alias for --node")
    package_docs.add_argument("--path", help="Explicit node directory path")
    package_docs.add_argument("--render", action="store_true", help="Render package diagrams/*.dot to images")
    package_docs.set_defaults(func=_dispatch_validate_package_docs)

    reindex = subparsers.add_parser("hook-reindex-knowledge", help="Refresh the private local knowledge search index")
    reindex.add_argument("--if-exists", action="store_true", help="Do nothing until the private index has been built once")
    reindex.set_defaults(func=_dispatch_hook_reindex_knowledge)

    search = subparsers.add_parser("knowledge-search", help="Retrieve ranked cited Hydra knowledge snippets")
    search.add_argument("text", help="Search query")
    search.add_argument("--budget", type=int, help="Approx-token budget")
    search.add_argument("--limit", type=int, help="Maximum candidate results before budget trimming")
    search.add_argument("--path", action="append", default=[], help="Exact path/touched-file hint")
    search.set_defaults(func=_dispatch_knowledge_search)

    brief = subparsers.add_parser("delegation-brief", help="Shape knowledge-search results into a subagent read-first brief")
    brief.add_argument("text", help="Goal or query")
    brief.add_argument("--budget", type=int, default=1500, help="Approx-token read budget")
    brief.add_argument("--limit", type=int, help="Maximum candidate results before budget trimming")
    brief.add_argument("--path", action="append", default=[], help="Exact path/touched-file hint")
    brief.set_defaults(func=_dispatch_delegation_brief)

    knowledge = subparsers.add_parser("knowledge", help="Inspect Hydra knowledge packages")
    knowledge_sub = knowledge.add_subparsers(dest="knowledge_command", required=True)
    knowledge_sub.add_parser("stale", help="Report stale knowledge-unit provenance sources").set_defaults(func=_dispatch_knowledge_stale)
    fingerprint = knowledge_sub.add_parser("fingerprint", help="Write source digests for one knowledge unit")
    fingerprint.add_argument("--unit", required=True, help="Knowledge-unit hydra_id to fingerprint")
    fingerprint.set_defaults(func=_dispatch_knowledge_fingerprint)


def _dispatch_measure_context(args, ctx) -> int:
    return command_measure_context(
        args,
        ctx.context_compiler_paths(),
        chars_per_token=ctx.threshold_value("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
    ).exit_code


def _dispatch_validate_package_docs(args, ctx) -> int:
    return command_validate_package_docs(
        args,
        ctx.context_compiler_paths(),
        ctx.resolver_paths(),
        ctx.command_ids,
        file_fail_tokens=ctx.threshold_value("hydra_engine.knowledge.package_checks.PACKAGE_FILE_FAIL_TOKENS"),
        chars_per_token=ctx.threshold_value("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
    ).exit_code


def _dispatch_hook_reindex_knowledge(args, ctx) -> int:
    return command_hook_reindex_knowledge(args, ctx.context_compiler_paths(), ctx.resolver_paths(), ctx.local, ctx.command_ids).exit_code


def _dispatch_knowledge_search(args, ctx) -> int:
    return command_knowledge_search(
        args,
        ctx.context_compiler_paths(),
        ctx.resolver_paths(),
        ctx.local,
        ctx.command_ids,
        default_budget=ctx.threshold_value("hydra_engine.knowledge.search_index.DEFAULT_BUDGET"),
        default_limit=ctx.threshold_value("hydra_engine.knowledge.search_index.DEFAULT_RESULT_LIMIT"),
        preview_chars=ctx.threshold_value("hydra_engine.knowledge.search_index.DEFAULT_PREVIEW_CHARS"),
        chars_per_token=ctx.threshold_value("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
    ).exit_code


def _dispatch_delegation_brief(args, ctx) -> int:
    return command_delegation_brief(
        args,
        ctx.context_compiler_paths(),
        ctx.resolver_paths(),
        ctx.local,
        ctx.command_ids,
        default_limit=ctx.threshold_value("hydra_engine.knowledge.search_index.DEFAULT_RESULT_LIMIT"),
        preview_chars=ctx.threshold_value("hydra_engine.knowledge.search_index.DEFAULT_PREVIEW_CHARS"),
        chars_per_token=ctx.threshold_value("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
    ).exit_code


def _dispatch_knowledge_stale(args, ctx) -> int:
    return command_knowledge_stale(args, ctx.context_compiler_paths()).exit_code


def _dispatch_knowledge_fingerprint(args, ctx) -> int:
    return command_knowledge_fingerprint(args, ctx.context_compiler_paths()).exit_code
