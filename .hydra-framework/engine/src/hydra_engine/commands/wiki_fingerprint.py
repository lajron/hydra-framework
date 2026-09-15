"""Write current source fingerprints for one human-wiki page."""

from __future__ import annotations

from datetime import date
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.digests import normalized_digest
from hydra_engine.documents.tokens import display_path, read_text, write_text
from hydra_engine.knowledge.freshness import resolve_source_path
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.wiki.sidecar_entries import SidecarParseError, read_sidecar_entries, replace_sidecar_fingerprint


def _sidecar_paths(paths: ContextCompilerPaths) -> list[Path]:
    return sorted((paths.hydra / "surfaces/wiki").glob("*.yaml"))


def _find_page(args, paths: ContextCompilerPaths):
    matches = []
    for sidecar in _sidecar_paths(paths):
        content = read_text(sidecar)
        for entry in read_sidecar_entries(sidecar, paths.root):
            if entry.hydra_id == args.page:
                matches.append((sidecar, content, entry))
    return matches


def command_wiki_fingerprint(args, paths: ContextCompilerPaths) -> CommandResult:
    try:
        matches = _find_page(args, paths)
    except (OSError, UnicodeError, SidecarParseError, ValueError) as error:
        print(f"Hydra wiki fingerprint: {error}", file=sys.stderr)
        return CommandResult(1)

    if not matches:
        print(f"Hydra wiki fingerprint: page not found: {args.page}", file=sys.stderr)
        return CommandResult(1)
    if len(matches) > 1:
        print(f"Hydra wiki fingerprint: duplicate hydra_id: {args.page}", file=sys.stderr)
        return CommandResult(1)

    sidecar, content, entry = matches[0]
    if not entry.sources:
        print(f"Hydra wiki fingerprint: page has no provenance.sources: {args.page}", file=sys.stderr)
        return CommandResult(1)

    fingerprints: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source in entry.sources:
        if source in seen:
            continue
        seen.add(source)
        source_path = resolve_source_path(source, paths)
        if not source_path.is_file():
            print(f"Hydra wiki fingerprint: source is not one existing file: {source}", file=sys.stderr)
            return CommandResult(1)
        try:
            fingerprints.append((source, normalized_digest(source_path)))
        except (OSError, UnicodeError) as error:
            print(f"Hydra wiki fingerprint: source could not be fingerprinted: {source}: {error}", file=sys.stderr)
            return CommandResult(1)

    checked_on = date.today().isoformat()
    try:
        updated = replace_sidecar_fingerprint(
            content,
            path=sidecar,
            root=paths.root,
            hydra_id=args.page,
            entries=fingerprints,
            checked_on=checked_on,
        )
    except (SidecarParseError, ValueError) as error:
        print(f"Hydra wiki fingerprint: {error}", file=sys.stderr)
        return CommandResult(1)
    write_text(sidecar, updated)

    print(f"Hydra wiki fingerprint: updated {display_path(sidecar, paths.root)}")
    for source, digest in fingerprints:
        print(f"- {source}: {digest}")
    return CommandResult(0)
