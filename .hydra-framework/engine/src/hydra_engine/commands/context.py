"""context command decisions: compile-context.

`prompt_from_stdin_or_arg` has a second real caller (`command_route_prompt`)
and is too small to be worth a delegator just for this one
caller -- matching `command_hook_token_pre_context`'s precomputed-data
pattern for a cross-cutting dependency owned elsewhere.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

from hydra_engine.commands import CommandResult
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN
from hydra_engine.knowledge.context_packets import DEFAULT_CONTEXT_BUDGET, compile_context_packet as _compile_context_packet
from hydra_engine.knowledge.context_providers import DEFAULT_FAMILY_CANDIDATE_CAP
from hydra_engine.knowledge.surfaces import measure_context_surfaces


@dataclass(frozen=True)
class PromptPayload:
    prompt: str
    session_id: str = ""


def prompt_payload_from_stdin_or_arg(args) -> PromptPayload:
    if getattr(args, "prompt", None):
        return PromptPayload(args.prompt)
    raw = sys.stdin.read()
    if not raw:
        return PromptPayload("")
    try:
        data = json.loads(raw)
        return PromptPayload(
            str(data.get("prompt") or data.get("message") or raw),
            str(data.get("session_id") or ""),
        )
    except json.JSONDecodeError:
        return PromptPayload(raw)


def prompt_from_stdin_or_arg(args) -> str:
    """Shared by `compile-context` (this module) and `route-prompt`
    (`cli.route_prompt`, which imports this rather than duplicating it --
    a downward/sideways import from the `cli` layer, not upward)."""
    return prompt_payload_from_stdin_or_arg(args).prompt


def compile_context_packet(
    *,
    task: str,
    paths,
    resolver_paths,
    provider: str = "",
    model: str = "",
    budget: int = DEFAULT_CONTEXT_BUDGET,
    node_values: list[str] | None = None,
    space: str = "",
    object_refs: list[str] | None = None,
    path_refs: list[str] | None = None,
    route_values: list[str] | None = None,
    view_values: list[str] | None = None,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
    family_cap: int = DEFAULT_FAMILY_CANDIDATE_CAP,
    include_families: list[str] | None = None,
    exclude_families: list[str] | None = None,
    command_ids: tuple[str, ...] = (),
) -> dict:
    rows, surface_totals = measure_context_surfaces(paths, chars_per_token=chars_per_token)
    return _compile_context_packet(
        task=task,
        paths=paths,
        resolver_paths=resolver_paths,
        surface_totals=surface_totals,
        surface_file_count=len(rows),
        provider=provider,
        model=model,
        budget=budget,
        node_values=node_values,
        space=space,
        object_refs=object_refs,
        path_refs=path_refs,
        route_values=route_values,
        view_values=view_values,
        chars_per_token=chars_per_token,
        family_cap=family_cap,
        include_families=include_families,
        exclude_families=exclude_families,
        command_ids=command_ids,
    )


def print_context_packet(packet: dict) -> None:
    print("Hydra context packet")
    print(f"Schema: {packet['schema']}")
    print(f"Date: {packet['date']}")
    print(f"Task: {packet['task']}")
    print(f"Provider/model: {packet['provider']} / {packet['model']}")
    print(f"Budget: {packet['budget_tokens']} approx tokens")

    print("Nodes:")
    if packet.get("nodes"):
        for item in packet["nodes"]:
            line = f"- {item['node']} ({item['reason']}): {item['title']}"
            if item.get("routes"):
                line += f" [routes: {', '.join(item['routes'])}]"
            print(line)
    else:
        print("- none")

    print("Selected context:")
    if packet["selected_context"]:
        for item in packet["selected_context"]:
            pointer = item.get("pointer", item["path"])
            line = f"- {pointer} [{item['kind']}, {item['approx_tokens']} approx tokens] - {item['reason']}"
            if item.get("hydra_id"):
                line += f"; {item['hydra_id']} ({item.get('status', 'unknown')})"
            if item.get("required"):
                line += " (required)"
            print(line)
    else:
        print("- none")

    stale_items = [
        item for item in [*packet["selected_context"], *packet["omitted_candidates"]]
        if item.get("stale_sources")
    ]
    if stale_items:
        print("Stale unit sources:")
        for item in stale_items:
            pointer = item.get("pointer", item["path"])
            source = item.get("hydra_id") or item.get("source")
            line = f"- {pointer}"
            if source:
                line += f"; {source}"
            line += f" [STALE: {', '.join(item['stale_sources'])} committed after checked_on]"
            print(line)

    if packet.get("required_units"):
        print("Required units:")
        for unit in packet["required_units"]:
            print(f"- {unit['hydra_id']} [{unit['approx_tokens']} approx tokens]")
        overage = packet["token_estimate"].get("required_overage", 0)
        if overage:
            print(f"- required_overage: +{overage} approx tokens over budget (not a failure)")

    if packet.get("avoid_by_default"):
        print("Avoid by default:")
        for value in packet["avoid_by_default"]:
            print(f"- {value}")

    if packet.get("verify"):
        print("Verify:")
        for value in packet["verify"]:
            print(f"- {value}")

    print("Omitted candidates:")
    if packet["omitted_candidates"]:
        for item in packet["omitted_candidates"]:
            print(f"- {item['path']} [{item['approx_tokens']} approx tokens] - {item['reason']}")
    else:
        print("- none")

    estimate = packet["token_estimate"]
    print("Token estimate:")
    print(f"- Always-loaded surfaces: {estimate['always_loaded_surfaces']}")
    print(f"- Selected context: {estimate['selected_context']}")
    print(f"- Total if loaded: {estimate['total_if_loaded']}")
    print(f"- Approximation: {estimate['approximation']}")

    freshness = packet["provenance_freshness"]
    print("Provenance and freshness:")
    print(f"- Resolver objects: {freshness['resolver_objects']}")
    if freshness["object_errors"]:
        for error in freshness["object_errors"]:
            print(f"- Object error: {error}")
    if freshness["registry_freshness_errors"]:
        for error in freshness["registry_freshness_errors"]:
            print(f"- Registry freshness warning: {error}")
    else:
        print("- Registry freshness: ok or no registry present")

    print("Validation reminders:")
    for item in packet["validation_reminders"]:
        print(f"- {item}")

    print("Known-risk reminders:")
    for item in packet["known_risk_reminders"]:
        print(f"- {item}")

    if packet["warnings"]:
        print("Warnings:")
        for warning in packet["warnings"]:
            print(f"- {warning}")


def command_compile_context(
    args,
    task: str,
    paths,
    resolver_paths,
    default_budget: int = DEFAULT_CONTEXT_BUDGET,
    default_family_cap: int = DEFAULT_FAMILY_CANDIDATE_CAP,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
    command_ids: tuple[str, ...] = (),
) -> CommandResult:
    if not task:
        print("Hydra context compiler: task text is required via --task, --prompt, or stdin", file=sys.stderr)
        return CommandResult(1)
    packet = compile_context_packet(
        task=task,
        paths=paths,
        resolver_paths=resolver_paths,
        provider=args.provider,
        model=args.model,
        budget=args.budget if args.budget is not None else default_budget,
        node_values=[*getattr(args, "node", []), *getattr(args, "package", [])],
        space=getattr(args, "space", "") or getattr(args, "domain", ""),
        object_refs=getattr(args, "object", []),
        path_refs=getattr(args, "path", []),
        route_values=getattr(args, "route", []),
        view_values=getattr(args, "view", []),
        chars_per_token=chars_per_token,
        family_cap=args.family_cap if args.family_cap is not None else default_family_cap,
        include_families=getattr(args, "include_family", []),
        exclude_families=getattr(args, "exclude_family", []),
        command_ids=command_ids,
    )
    route_errors = [
        warning for warning in packet["warnings"]
        if warning.startswith(("Route ", "Knowledge graph error:", "Knowledge binding error:", "Knowledge view error:"))
    ]
    if route_errors:
        for warning in route_errors:
            print(warning, file=sys.stderr)
        return CommandResult(1)
    if args.json:
        print(json.dumps(packet, indent=2))
    else:
        print_context_packet(packet)
    return CommandResult(0)


def register(subparsers) -> None:
    """Add `compile-context`."""
    compile_context = subparsers.add_parser("compile-context", help="Build a bounded Knowledge v3 context packet")
    compile_context.add_argument("--task", default="", help="Task text to compile context for")
    compile_context.add_argument("--prompt", default="", help="Alias for --task; if both are omitted, stdin is read")
    compile_context.add_argument("--provider", default="", help="Provider name for the packet metadata")
    compile_context.add_argument("--model", default="", help="Model name for the packet metadata")
    compile_context.add_argument("--budget", type=int, help="Approx-token budget for selected context")
    compile_context.add_argument("--node", action="append", default=[], help="Knowledge node id or unambiguous leaf slug to include")
    compile_context.add_argument("--space", default="", help="Knowledge space to include")
    compile_context.add_argument("--package", action="append", default=[], help="Deprecated alias for --node")
    compile_context.add_argument("--domain", default="", help="Deprecated alias for --space")
    compile_context.add_argument("--object", action="append", default=[], help="Relevant hydra:// object ID or alias to include")
    compile_context.add_argument("--path", action="append", default=[], help="Relevant repository file path to include")
    compile_context.add_argument("--route", action="append", default=[], help="Node-qualified route to activate, as <node>:<route>")
    compile_context.add_argument("--view", action="append", default=[], help="Knowledge view id or slug to compose")
    compile_context.add_argument("--family-cap", type=int, help="Max candidates one non-Knowledge context-provider family may contribute")
    compile_context.add_argument("--include-family", action="append", default=[], help="Restrict context providers to this object family (repeatable); default is every registered family")
    compile_context.add_argument("--exclude-family", action="append", default=[], help="Drop this object family's context provider (repeatable)")
    compile_context.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    compile_context.set_defaults(func=_dispatch_compile_context)


def _dispatch_compile_context(args, ctx) -> int:
    task = args.task or args.prompt or prompt_from_stdin_or_arg(args)
    return command_compile_context(
        args,
        task,
        ctx.context_compiler_paths(),
        ctx.resolver_paths(),
        default_budget=ctx.threshold_value("hydra_engine.knowledge.context_packets.DEFAULT_CONTEXT_BUDGET"),
        default_family_cap=ctx.threshold_value("hydra_engine.knowledge.context_providers.DEFAULT_FAMILY_CANDIDATE_CAP"),
        chars_per_token=ctx.threshold_value("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
        command_ids=ctx.command_ids,
    ).exit_code
