"""object_moves command decisions: move-object.

`resolver_paths: ObjectLocations` is a bare forward-reference type hint (no
real import), matching the established codebase-wide convention.
`stale_path_citations` is an exclusive helper, moved with the command
(grepped first: no other caller anywhere in the tree). `resolved_envelope_path`
moved to `objects.envelopes` instead, beside its inverse `object_display_path`,
since `commands.schema` needs it too and a commands-module-importing-a-
commands-module shape would be the wrong direction for the same reason
`write_object_registry` landed in `objects.registry` rather than in this
module or `commands.references`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path, read_text, write_text
from hydra_engine.objects import envelopes as envelopes_engine
from hydra_engine.objects.discovery import collect_hydra_objects, object_metadata_paths
from hydra_engine.objects.envelopes import object_display_path, object_state_tier, resolved_envelope_path
from hydra_engine.objects.references import validate_object_references
from hydra_engine.objects.registry import write_object_registry
from hydra_engine.providers import reclaim
from hydra_engine.providers.paths import ProvidersPaths


def stale_path_citations(old_display_path: str, resolver_paths) -> list[str]:
    """Files that still name the pre-move path in prose or metadata.

    Reported rather than rewritten: Markdown path links stay a
    correct reference form, so which of them should follow the file and which
    were pointing at that location on purpose is a human call.
    """
    citations: list[str] = []
    for path in object_metadata_paths(resolver_paths):
        try:
            if old_display_path in read_text(path):
                citations.append(display_path(path, resolver_paths.root))
        except OSError:
            continue
    return citations


def command_move_object(args, resolver_paths) -> CommandResult:
    """Move one canonical object and refresh the registry entry it owns.

    This is the canonical path for an intentional move. It
    relocates the file and rewrites derived state only; `hydra_id` and `uid`
    are never touched, which is exactly what lets `ref check` recognize the
    result as the same object rather than a delete plus an add.
    """
    # One scan shared with the reference check below:
    # nothing between them mutates the tree, so the second scan was a repeat.
    objects, discovery_errors = collect_hydra_objects(resolver_paths)
    findings = validate_object_references(resolver_paths, objects_result=(objects, discovery_errors))
    if findings:
        print("Hydra move-object: failed", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return CommandResult(1)

    base = Path.cwd() if (Path.cwd() / args.source).exists() else resolver_paths.root
    source = Path(args.source) if Path(args.source).is_absolute() else base / args.source
    if not source.is_file():
        print(f"Hydra move-object: source is not a file: {args.source}", file=sys.stderr)
        return CommandResult(1)

    source_display = object_display_path(source, resolver_paths)
    matches = [obj for obj in objects if obj["path"] == source_display]
    if not matches:
        print(f"Hydra move-object: {source_display} is not a canonical Hydra object", file=sys.stderr)
        return CommandResult(1)
    obj = matches[0]
    if not obj["uid"]:
        print(
            f"Hydra move-object: {source_display} has no uid; run `hydra.py schema upgrade` first",
            file=sys.stderr,
        )
        return CommandResult(1)

    destination = Path(args.destination) if Path(args.destination).is_absolute() else base / args.destination
    if destination.is_dir() or args.destination.endswith(("/", os.sep)):
        destination = destination / source.name
    if destination.exists():
        print(f"Hydra move-object: destination already exists: {object_display_path(destination, resolver_paths)}", file=sys.stderr)
        return CommandResult(1)
    if destination.suffix != source.suffix:
        # Object discovery is extension-driven, so a changed suffix would
        # silently unregister the object rather than relocate it.
        print(
            f"Hydra move-object: destination must keep the `{source.suffix}` suffix: {args.destination}",
            file=sys.stderr,
        )
        return CommandResult(1)

    destination_tier = object_state_tier(destination, resolver_paths)
    if destination_tier != obj["tier"]:
        print(
            f"Hydra move-object: destination changes state tier ({obj['tier']} -> {destination_tier}); "
            "a tier change requires the placement rules, not a move",
            file=sys.stderr,
        )
        return CommandResult(1)

    destination_display = object_display_path(destination, resolver_paths)
    sidecar: Path | None = None
    sidecar_text = ""
    if obj["envelope_path"] != obj["path"]:
        # A sidecar records the object's path itself, so the move is only
        # complete once that record points at the new location too.
        sidecar = resolved_envelope_path(obj["envelope_path"], resolver_paths)
        sidecar_text, changed = envelopes_engine.replace_envelope_field(
            read_text(sidecar), obj["id"], "path", destination_display
        )
        if not changed:
            print(
                f"Hydra move-object: could not rewrite the path for `{obj['id']}` in {obj['envelope_path']}",
                file=sys.stderr,
            )
            return CommandResult(1)

    if args.dry_run:
        print(f"Would move `{obj['id']}`: {source_display} -> {destination_display}")
        if sidecar:
            print(f"Would rewrite sidecar path: {obj['envelope_path']}")
        return CommandResult(0)

    sidecar_before = read_text(sidecar) if sidecar else ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    if sidecar:
        write_text(sidecar, sidecar_text)

    findings = validate_object_references(resolver_paths)
    if findings:
        # Put the tree back rather than leave a half-applied move behind: a
        # broken object graph is worse than a refused command.
        destination.rename(source)
        if sidecar:
            write_text(sidecar, sidecar_before)
        print(f"Hydra move-object: {source_display} -> {destination_display} would break references; reverted", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return CommandResult(1)

    count = write_object_registry(resolver_paths)
    print(f"Moved `{obj['id']}`: {source_display} -> {destination_display}")
    if count is None:
        print("note: registry write refused (concurrent change detected); rerun `hydra.py ref index`", file=sys.stderr)
    else:
        print(f"Indexed {count} objects: {display_path(resolver_paths.object_registry, resolver_paths.root)}")
    for note in stale_path_citations(source_display, resolver_paths):
        print(f"note: {note} still cites {source_display}")
    if obj["kind"] in ("skill", "agent") and source.parent.name != destination.parent.name:
        # A canonical skill/agent rename leaves its old wrapper's canonical
        # source gone, so nothing can ever prove ownership of it again (see
        # `providers.reclaim`'s report-only stale contract). Print the same
        # removal line `reclaim`/`validate` would surface on their next run,
        # rather than waiting for one.
        providers_paths = ProvidersPaths(root=resolver_paths.root, hydra=resolver_paths.hydra)
        for line in reclaim.stale_wrapper_notices(providers_paths, source.parent.name, obj["kind"]):
            print(line)
    return CommandResult(0)


def register(subparsers) -> None:
    """Add `move-object`."""
    move_object = subparsers.add_parser("move-object", help="Move a canonical Hydra object and refresh its registry entry")
    move_object.add_argument("source", help="Current path of the canonical object file")
    move_object.add_argument("destination", help="New path, or an existing directory to move into")
    move_object.add_argument("--dry-run", action="store_true", help="Report the move without performing it")
    move_object.set_defaults(func=_dispatch_move_object)


def _dispatch_move_object(args, ctx) -> int:
    return command_move_object(args, ctx.resolver_paths()).exit_code
