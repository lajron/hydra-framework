"""Generated-plus-annotated command metadata.

Mechanical fields (`id`, `aliases`, `arguments`) are derived by walking the
already-built argparse tree, so they can never drift from what `COMMAND_MODULES`
actually registers the way a hand-copied parallel YAML would. Judgment fields
(`side_effects`/`confirmation`/`privacy`) are hand-authored in
`SIDE_EFFECT_COMMANDS` below, and only for commands with a real side effect --
read-only reporting commands stay mechanical-only.
"""

from __future__ import annotations

import argparse
import dataclasses
import json

from hydra_engine.cli import parser as cli_parser


@dataclasses.dataclass(frozen=True)
class CommandSafety:
    side_effects: str
    confirmation: str
    privacy: str


@dataclasses.dataclass(frozen=True)
class CommandMetadata:
    id: str
    aliases: tuple[str, ...]
    arguments: tuple[str, ...]
    safety: CommandSafety | None


SIDE_EFFECT_COMMANDS: dict[str, CommandSafety] = {
    "summarize-log": CommandSafety(
        side_effects="writes the full input log under .hydra-framework.local/logs/ when --store-full is given",
        confirmation="none needed; opt-in flag, private destination",
        privacy="private (.hydra-framework.local/)",
    ),
    "retry-guard": CommandSafety(
        side_effects="writes failure-fingerprint state under .hydra-framework.local/",
        confirmation="none needed; local bookkeeping only",
        privacy="private (.hydra-framework.local/)",
    ),
    "hook-command-output": CommandSafety(
        side_effects="writes structural reducer telemetry under .hydra-framework.local/telemetry/ and writes the full Bash output under .hydra-framework.local/logs/ only when private policy enables full-log storage",
        confirmation="none needed; private destination and silent by default",
        privacy="private (.hydra-framework.local/) for optional full logs; model-visible output is reduced before provider context",
    ),
    "hook-codex-command-output": CommandSafety(
        side_effects="writes structural reducer telemetry under .hydra-framework.local/telemetry/ and writes the full Bash output under .hydra-framework.local/logs/ only when private policy enables full-log storage",
        confirmation="none needed; private destination and silent by default",
        privacy="private (.hydra-framework.local/) for optional full logs; model-visible output is reduced before provider context",
    ),
    "hook-retry-guard": CommandSafety(
        side_effects="writes failure-fingerprint state under .hydra-framework.local/",
        confirmation="none needed; local bookkeeping only",
        privacy="private (.hydra-framework.local/)",
    ),
    "hook-codex-retry-guard": CommandSafety(
        side_effects="writes failure-fingerprint state under .hydra-framework.local/",
        confirmation="none needed; local bookkeeping only",
        privacy="private (.hydra-framework.local/)",
    ),
    "hook-token command-result": CommandSafety(
        side_effects="writes failure-fingerprint state under .hydra-framework.local/ when the command failed, "
        "and the full input log there when --store-full (or policy) is set",
        confirmation="none needed; opt-in/derived flags, private destination",
        privacy="private (.hydra-framework.local/)",
    ),
    "hook-post-edit": CommandSafety(
        side_effects="writes rendered diagram images (images/*.svg, images/*.png) next to a package's diagrams/*.dot when --render is given",
        confirmation="none needed; regenerable, tracked build output",
        privacy="shared (tracked repository files)",
    ),
    "hook-reindex-knowledge": CommandSafety(
        side_effects="writes the private SQLite knowledge index under .hydra-framework.local/index/",
        confirmation="none needed; private rebuildable index",
        privacy="private (.hydra-framework.local/)",
    ),
    "knowledge-search": CommandSafety(
        side_effects="increments private command-usage counters under .hydra-framework.local/telemetry/",
        confirmation="none needed; local aggregate counts only",
        privacy="private (.hydra-framework.local/), no prompt text",
    ),
    "delegation-brief": CommandSafety(
        side_effects="increments private command-usage counters under .hydra-framework.local/telemetry/",
        confirmation="none needed; local aggregate counts only",
        privacy="private (.hydra-framework.local/), no prompt text",
    ),
    "route-prompt": CommandSafety(
        side_effects="increments private route hit/miss counters under .hydra-framework.local/telemetry/",
        confirmation="none needed; local aggregate counts only",
        privacy="private (.hydra-framework.local/), no prompt text",
    ),
    "telemetry gate": CommandSafety(
        side_effects="reads private telemetry rows and writes an attestation JSON only when --output is given",
        confirmation="none needed; attestation contains counts, field names, digest, verdict, and date, not private corpus paths",
        privacy="private corpus input; output is path chosen by the caller",
    ),
    "telemetry evidence create": CommandSafety(
        side_effects="reads private telemetry rows and creates a new tracked directory under .hydra-framework/repo/telemetry/packages/",
        confirmation="none needed; refuses outright when the gate verdict is `fail`, and writes only derived aggregates, never a raw row",
        privacy="private corpus input; output is a shared, tracked package (counts, field names, digest, verdict, and date, not private corpus paths)",
    ),
    "adopt": CommandSafety(
        side_effects="writes lineage into manifest.yaml when --record is given",
        confirmation="confirm before running unattended; changes tracked adoption lineage",
        privacy="shared (tracked repository files)",
    ),
    "init": CommandSafety(
        side_effects="copies this Hydra framework's files into another repository, overwriting existing files when --force is given",
        confirmation="confirm before running unattended; writes outside this repository",
        privacy="shared (files written into the target repository)",
    ),
    "init-local": CommandSafety(
        side_effects="writes the shared .gitignore rule and seeds missing files under .hydra-framework.local/",
        confirmation="none needed; additive and does not overwrite private files",
        privacy="shared (.gitignore) and private (.hydra-framework.local/)",
    ),
    "install-hooks": CommandSafety(
        side_effects="sets or (with --uninstall) unsets Git's core.hooksPath for this clone",
        confirmation="none needed; per-clone convenience, reversible with --uninstall",
        privacy="private (local Git config, not tracked)",
    ),
    "migration ledger": CommandSafety(
        side_effects="creates the shared intake migration workspace under .hydra-framework/intake/migrations/ when --create is given",
        confirmation="none needed; additive and refuses an existing workspace",
        privacy="shared (tracked repository files)",
    ),
    "migration request-stage": CommandSafety(
        side_effects="writes a bounded shared approval-state request after read-only source inventory; it does not move source material",
        confirmation="human approval is recorded separately with migration decide approve before any move",
        privacy="shared audit state; sensitive findings are grouped rather than copied",
    ),
    "migration propose": CommandSafety(
        side_effects="writes a digest-bound package/unit proposal into the bounded migration workspace; it does not publish canonical files",
        confirmation="human approval follows fresh independent validation",
        privacy="shared proposal and audit state; only material already prepared for canonical review belongs here",
    ),
    "migration validate-batch": CommandSafety(
        side_effects="records independent validation evidence and writes a bounded publication approval request",
        confirmation="human approval is still required before canonical publication",
        privacy="shared validation evidence and audit state",
    ),
    "migration request-close": CommandSafety(
        side_effects="writes a full reconciliation and exact staged-original removal request; it does not remove originals",
        confirmation="human approval is recorded separately before removal",
        privacy="shared audit state; private-sensitive items must remain grouped",
    ),
    "migration decide": CommandSafety(
        side_effects="records approve, reject, or revise; approve immediately applies the current digest-bound staging, publication, or exact-removal action",
        confirmation="explicit human outcome required; approve may move sources, publish canonical files, or remove reconciled staged originals",
        privacy="shared audit state plus the staging tier and canonical targets named by the approved action",
    ),
    "integrate identify": CommandSafety(
        side_effects="rewrites object-map.yaml in an existing source integration workspace",
        confirmation="none needed; additive workspace state, source tree is not modified",
        privacy="shared (tracked repository files)",
    ),
    "integrate map": CommandSafety(
        side_effects="creates the shared source integration workspace under .hydra-framework/intake/integrations/ when --create is given",
        confirmation="none needed; additive, idempotent",
        privacy="shared (tracked repository files)",
    ),
    "move-object": CommandSafety(
        side_effects="renames a canonical object file and its sidecar, unless --dry-run is given",
        confirmation="confirm before running unattended; rewrites a tracked file path",
        privacy="shared (tracked repository files)",
    ),
    "export-adapters": CommandSafety(
        side_effects=(
            "writes generated provider skill/subagent wrapper files, and deletes wrapper units a narrower "
            "capability profile no longer selects, unless --check or --dry-run is given"
        ),
        confirmation="none needed; regenerable, and deletion is limited to units Hydra can prove it owns (see the six ownership conditions)",
        privacy="local working tree only; generated output is Git-ignored and never tracked",
    ),
    "profile select": CommandSafety(
        side_effects="writes .hydra-framework.local/capabilities/active.yaml, then reconciles adapters under the same lock as export-adapters, including deletion",
        confirmation="none needed; reconciliation follows the same ownership-proven deletion as export-adapters, and a crash mid-way is recovered by an ordinary export-adapters",
        privacy="private selection (.hydra-framework.local/) and local working tree for the Git-ignored adapters it materializes",
    ),
    "reclaim": CommandSafety(
        side_effects="moves hand-authored provider files into canonical Hydra when --promote is given",
        confirmation="confirm before running unattended; moves and rewrites tracked files",
        privacy="shared (tracked repository files)",
    ),
    "ref index": CommandSafety(
        side_effects="overwrites the derived object registry file",
        confirmation="none needed; regenerable, tracked build output",
        privacy="shared (tracked repository files)",
    ),
    "ref store rebuild": CommandSafety(
        side_effects="writes the private SQLite object-graph store under .hydra-framework.local/index/",
        confirmation="none needed; private, disposable, rebuildable from the tracked export",
        privacy="private (.hydra-framework.local/)",
    ),
    "schema upgrade": CommandSafety(
        side_effects="rewrites every canonical object's envelope to the current schema_version",
        confirmation="confirm before running unattended; broad rewrite across tracked objects",
        privacy="shared (tracked repository files)",
    ),
    "evolution record": CommandSafety(
        side_effects="appends an entry to the adaptation ledger",
        confirmation="none needed; additive, append-only",
        privacy="shared (tracked repository files)",
    ),
    "wiki scaffold": CommandSafety(
        side_effects="creates project-wiki/<project> starter pages, overwriting existing ones when --force is given",
        confirmation="confirm before running unattended with --force; otherwise additive",
        privacy="shared (tracked repository files)",
    ),
    "capability scaffold-skill": CommandSafety(
        side_effects="creates a canonical skill module, overwriting its metadata and body when --force is given, then rebuilds the derived object registry",
        confirmation="confirm before running unattended with --force; otherwise additive",
        privacy="shared (tracked repository files)",
    ),
    "capability scaffold-agent": CommandSafety(
        side_effects="creates a canonical agent module, overwriting its metadata and body when --force is given, then rebuilds the derived object registry",
        confirmation="confirm before running unattended with --force; otherwise additive",
        privacy="shared (tracked repository files)",
    ),
    "note": CommandSafety(
        side_effects="creates or reuses a dated titled private note file; stdin-only input appends to today's scratch note",
        confirmation="none needed; private, append-only",
        privacy="private (.hydra-framework.local/)",
    ),
    "migrate-state": CommandSafety(
        side_effects="moves, deletes, or retires task and tier state when --apply is given; overwrites destination "
        "conflicts when --force is also given",
        confirmation="confirm before running unattended with --apply; --force can overwrite",
        privacy="shared and private (moves state between .hydra-framework/ and .hydra-framework.local/)",
    ),
    "task start": CommandSafety(
        side_effects="creates a personal task record file and stages it for Git tracking when possible",
        confirmation="none needed; additive, owner-scoped",
        privacy="shared (tracked repository files)",
    ),
    "task checkpoint": CommandSafety(
        side_effects="creates a checkpoint file beside a task record and stages the checkpoint/task update when possible",
        confirmation="none needed; additive, owner-scoped",
        privacy="shared (tracked repository files)",
    ),
    "task handoff": CommandSafety(
        side_effects="moves a task record into another owner's directory",
        confirmation="confirm before running unattended; reassigns another owner's state",
        privacy="shared (tracked repository files)",
    ),
    "task complete": CommandSafety(
        side_effects="deletes a task record file and its checkpoints only when Git can recover their current indexed content, stages those deletions when possible, and prints post-completion Git status",
        confirmation="none needed for your own task; confirm before completing another owner's",
        privacy="shared (tracked repository files)",
    ),
}


def _subparsers_action(parser: argparse.ArgumentParser) -> "argparse._SubParsersAction | None":
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _own_arguments(parser: argparse.ArgumentParser) -> tuple[str, ...]:
    names = []
    for action in parser._actions:
        if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
            continue
        names.append(action.option_strings[0] if action.option_strings else action.dest)
    return tuple(names)


def _direct_subcommands(action: "argparse._SubParsersAction") -> list[tuple[str, list[str], argparse.ArgumentParser]]:
    # Two names mapping to the same parser instance is how argparse represents
    # `add_parser(..., aliases=[...])`; grouping by `id(sub)` recovers that.
    primary: dict[int, str] = {}
    aliases: dict[int, list[str]] = {}
    order: list[int] = []
    for name, sub in action.choices.items():
        key = id(sub)
        if key not in primary:
            primary[key] = name
            aliases[key] = []
            order.append(key)
        elif name != primary[key]:
            aliases[key].append(name)
    return [(primary[key], aliases[key], action.choices[primary[key]]) for key in order]


def _walk(parser: argparse.ArgumentParser, prefix: tuple[str, ...]) -> list[CommandMetadata]:
    action = _subparsers_action(parser)
    if action is None:
        command_id = " ".join(prefix)
        return [CommandMetadata(
            id=command_id,
            aliases=(),
            arguments=_own_arguments(parser),
            safety=SIDE_EFFECT_COMMANDS.get(command_id),
        )]
    entries: list[CommandMetadata] = []
    for name, command_aliases, sub in _direct_subcommands(action):
        sub_entries = _walk(sub, prefix + (name,))
        if command_aliases and len(sub_entries) == 1:
            sub_entries = [dataclasses.replace(sub_entries[0], aliases=tuple(command_aliases))]
        entries.extend(sub_entries)
    return entries


def generate_command_metadata(parser: argparse.ArgumentParser) -> list[CommandMetadata]:
    return sorted(_walk(parser, ()), key=lambda entry: entry.id)


def _as_dict(entry: CommandMetadata) -> dict:
    data = {"id": entry.id, "aliases": list(entry.aliases), "arguments": list(entry.arguments)}
    if entry.safety is not None:
        data["side_effects"] = entry.safety.side_effects
        data["confirmation"] = entry.safety.confirmation
        data["privacy"] = entry.safety.privacy
    return data


def render(entries: list[CommandMetadata], as_json: bool = False) -> str:
    if as_json:
        return json.dumps([_as_dict(entry) for entry in entries], indent=2)
    lines: list[str] = []
    for entry in entries:
        lines.append(f"{entry.id} -- arguments: {' '.join(entry.arguments) or '(none)'}")
        if entry.aliases:
            lines.append(f"  aliases: {', '.join(entry.aliases)}")
        if entry.safety is not None:
            lines.append(f"  side_effects: {entry.safety.side_effects}")
            lines.append(f"  confirmation: {entry.safety.confirmation}")
            lines.append(f"  privacy: {entry.safety.privacy}")
    return "\n".join(lines)


def dispatch(args, command_modules) -> int:
    entries = generate_command_metadata(cli_parser.build_parser(command_modules))
    print(render(entries, as_json=args.json))
    return 0
