"""`route-prompt`'s own CLI-layer home.

This command cannot have a `commands/*.py` home: it
composes `knowledge.routing`'s package pointers with `work.board`'s state
lines and then calls `cli.rendering.render_route_prompt` -- and a
`commands/*.py` (layer 4) module importing `cli.rendering` (layer 5) would be
an upward import under architecture check 3. Its natural home is
the `cli` layer itself, sideways from `cli.rendering`, downward from
`knowledge.routing`/`work.board`/`commands.context` -- never upward.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import time

from hydra_engine.cli.rendering import render_route_prompt
from hydra_engine.commands.context import prompt_payload_from_stdin_or_arg
from hydra_engine.knowledge import search_index
from hydra_engine.knowledge.routing import route_prompt_node_pointers
from hydra_engine.knowledge.routing_diagnostics import route_prompt_match_diagnostics
from hydra_engine.ports import fs
from hydra_engine.work.board import state_pointer_lines

ROUTE_EMISSIONS_FILE = "route-emissions.jsonl"
ROUTE_PROMPT_REEMIT_EVERY = 25


def _capture_stamp(paths, local):
    """Load the operation-scoped read stamp without widening static fan-out."""
    return __import__("hydra_engine.knowledge.index_cache", fromlist=("capture_stamp",)).capture_stamp(paths, local)


def _open_knowledge_snapshot():
    return __import__("hydra_engine.knowledge.snapshot", fromlist=("open_knowledge_snapshot",)).open_knowledge_snapshot


def _route_once(prompt: str, ctx, max_routed_nodes: int, *, force_source: bool = False):
    """Run one search+routing pass pinned to a single read stamp.

    Returns `(matches, warnings, exact_references, stamp)`. `stamp` is `None`
    whenever this pass is already canonical (`force_source`, or the cache
    degraded on its own), meaning the caller has nothing left to revalidate.
    """
    paths = ctx.context_compiler_paths()
    if force_source:
        results, _features, _source = search_index.search(
            prompt, paths=paths, resolver_paths=ctx.resolver_paths(), local=ctx.local,
            command_ids=ctx.command_ids, limit=20, force_source=True,
        )
        stamp = None
    else:
        # Reuse the settled `Fresh` cache state as the opening stamp when the
        # search itself answered from it (D8/D20): this shares the one Git
        # fingerprint read `cache_state` already did instead of pinning a
        # second, independent one microseconds later. Captured only once the
        # search has settled, including any self-heal rebuild it triggered,
        # so the stamp still pins the exact publication the snapshot below
        # opens.
        results, _features, _source, reusable_stamp = search_index.search_for_context_provider(
            prompt, paths=paths, resolver_paths=ctx.resolver_paths(), local=ctx.local,
            command_ids=ctx.command_ids, limit=20,
        )
        stamp = reusable_stamp if reusable_stamp is not None else _capture_stamp(paths, ctx.local)
    open_knowledge_snapshot = _open_knowledge_snapshot()
    snapshot_warnings: list[str] = []
    try:
        snapshot = open_knowledge_snapshot(paths, stamp.publication if stamp is not None else None, _source, stamp=stamp)
        with snapshot:
            nodes = list(snapshot.routing_nodes(results))
            bindings = snapshot.bindings()
    except ValueError as error:
        if error.__class__.__name__ != "HydrationMismatch":
            # Exact references remain useful if optional v3 routing fails.
            nodes, bindings = [], {}
            snapshot_warnings.append(f"Knowledge v3 routing unavailable: {error}")
            stamp = None
        else:
            # A single source rerun prevents cache/source graph mixing.
            results, _features, _source = search_index.search(
                prompt, paths=paths, resolver_paths=ctx.resolver_paths(), local=ctx.local,
                command_ids=ctx.command_ids, limit=20, force_source=True,
            )
            stamp = None
            with open_knowledge_snapshot(paths, None, _source) as snapshot:
                nodes, bindings = list(snapshot.routing_nodes(results)), snapshot.bindings()
    # `search` already resolves exact ids and paths before ranking.  Reusing
    # that one result set avoids a second whole-corpus collection per hook.
    exact_references = [result for result in results if result.channel == "exact"]
    matches, match_warnings = route_prompt_node_pointers(
        prompt, paths, search_results=tuple(results), max_routed_nodes=max_routed_nodes,
        bindings=bindings, nodes=nodes,
    )
    return matches, [*snapshot_warnings, *match_warnings], exact_references, stamp


def command_route_prompt(args, ctx) -> int:
    payload = prompt_payload_from_stdin_or_arg(args)
    prompt = payload.prompt
    if not prompt:
        return 0
    started = time.perf_counter()
    as_json = bool(getattr(args, "json", False))
    max_routed_nodes = ctx.threshold_value("hydra_engine.knowledge.routing.MAX_ROUTED_NODES")
    matches, warnings, exact_references, stamp = _route_once(prompt, ctx, max_routed_nodes)
    if (
        stamp is not None and stamp.publication is not None
        and _capture_stamp(ctx.context_compiler_paths(), ctx.local) != stamp
    ):
        # The governed corpus or the published index moved between the
        # search above and this check, spanning routing and reference
        # resolution: discard the pinned-cache result and rerun once from
        # canonical sources rather than emit a decision that mixes two
        # generations of the cached graph.
        matches, warnings, exact_references, _stamp = _route_once(prompt, ctx, max_routed_nodes, force_source=True)
    match_reason = "global index" if matches else "none"
    reflections_dir = ctx.hydra / "evolution" / "reflections"
    telemetry_packages_dir = ctx.hydra / "repo" / "telemetry" / "packages"
    state_lines = state_pointer_lines(ctx.work_paths(), ctx.env_owner(), ctx.git_email(), reflections_dir, telemetry_packages_dir)
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        render_route_prompt(matches, warnings, state_lines, exact_references[:5])
    rendered_stdout = stdout.getvalue()
    rendered_stderr = stderr.getvalue()
    # A `--json` call is a diagnostic inspection, not a hook turn: it must not
    # perturb the session-scoped suppression state a real hook turn advances.
    should_emit = _should_emit(ctx.local, payload.session_id, rendered_stdout + rendered_stderr, record=not as_json)
    search_index.record_route(
        ctx.local,
        bool(matches),
        package_count=len(matches),
        match_reason=match_reason,
        reference_count=len(exact_references),
        suppressed=not should_emit,
    )
    if as_json:
        diagnostics = {
            "matches": _match_diagnostics(prompt, ctx, matches, match_reason),
            "warnings": warnings,
            "exact_references": [
                {"hydra_id": reference.document.hydra_id, "title": reference.document.title, "path": reference.document.path}
                for reference in exact_references
            ],
            "suppressed": not should_emit,
            "timing_ms": round((time.perf_counter() - started) * 1000, 3),
        }
        print(json.dumps(diagnostics, sort_keys=True))
        return 0
    if should_emit:
        print(rendered_stdout, end="")
        print(rendered_stderr, end="", file=sys.stderr)
    return 0


def _match_diagnostics(prompt: str, ctx, matches, match_reason: str) -> list[dict]:
    if not matches:
        return []
    matched_titles = {match.title for match in matches}
    scored = route_prompt_match_diagnostics(prompt, ctx.context_compiler_paths())
    return [{**entry, "reason": match_reason} for entry in scored if entry["title"] in matched_titles]


def _should_emit(local, session_id: str, rendered: str, *, record: bool = True) -> bool:
    if not session_id or not rendered:
        return True
    path = local / "monitoring" / ROUTE_EMISSIONS_FILE
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    count = 0
    last_digest = ""
    try:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("session_id") != session_id:
                    continue
                count += 1
                last_digest = str(event.get("digest") or "")
    except OSError:
        return True

    should_emit = digest != last_digest or (count > 0 and count % ROUTE_PROMPT_REEMIT_EVERY == 0)
    if not record:
        return should_emit
    try:
        fs.append_line(path, json.dumps({"session_id": session_id, "digest": digest, "turn": count + 1}, sort_keys=True))
    except OSError:
        return True
    return should_emit


def register(subparsers) -> None:
    route = subparsers.add_parser("route-prompt", help="Emit tiny Knowledge v3 node pointers for a prompt")
    route.add_argument("--prompt", default="", help="Prompt text; if omitted, stdin is read")
    route.add_argument(
        "--json", action="store_true",
        help="Print a diagnostic JSON object (matched nodes with reason/score, resolved exact "
        "references, suppression state, timing) instead of the plain hook output",
    )
    route.set_defaults(func=_dispatch_route_prompt)


def _dispatch_route_prompt(args, ctx) -> int:
    return command_route_prompt(args, ctx)
