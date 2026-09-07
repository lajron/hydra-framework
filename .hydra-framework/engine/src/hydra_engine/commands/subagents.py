"""Subagent lifecycle hook commands."""

from __future__ import annotations

import json
import sys

from hydra_engine.agent_hooks.subagent_context import SUBAGENT_CONTEXT_AGENT_TYPES, SUBAGENT_CONTEXT_TOKEN_BUDGET, build_subagent_context
from hydra_engine.commands import CommandResult
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN
from hydra_engine.knowledge.nodes import discover_knowledge_nodes
from hydra_engine.knowledge.packages import ContextCompilerPaths


def command_hook_subagent_start(
    args,
    paths: ContextCompilerPaths,
    token_budget: int | None = None,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> CommandResult:
    raw = sys.stdin.read()
    if not raw:
        return CommandResult(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return CommandResult(0)
    if not isinstance(data, dict) or data.get("hook_event_name") != "SubagentStart":
        return CommandResult(0)
    if str(data.get("agent_type") or "") not in SUBAGENT_CONTEXT_AGENT_TYPES:
        return CommandResult(0)

    package_names = [node.logical_id for node in discover_knowledge_nodes(paths) if node.routable]
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": build_subagent_context(
                package_names,
                token_budget=token_budget or SUBAGENT_CONTEXT_TOKEN_BUDGET,
                chars_per_token=chars_per_token,
            ),
        }
    }
    print(json.dumps(payload))
    return CommandResult(0)


def register(subparsers) -> None:
    subagent_start = subparsers.add_parser(
        "hook-subagent-start",
        help="Provider subagent-start injector; gives context-less subagents bounded Hydra discovery pointers",
    )
    subagent_start.set_defaults(func=_dispatch_hook_subagent_start)


def _dispatch_hook_subagent_start(args, ctx) -> int:
    return command_hook_subagent_start(
        args,
        ctx.context_compiler_paths(),
        token_budget=ctx.threshold_value("hydra_engine.agent_hooks.subagent_context.SUBAGENT_CONTEXT_TOKEN_BUDGET"),
        chars_per_token=ctx.threshold_value("hydra_engine.knowledge.candidates.APPROX_CHARS_PER_TOKEN"),
    ).exit_code
