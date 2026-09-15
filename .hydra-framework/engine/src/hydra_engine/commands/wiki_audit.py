"""Report freshness and provenance gaps in human-wiki sidecars."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path
from hydra_engine.knowledge.freshness import resolve_source_path, stale_provenance_sources
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.ports import git as git_port
from hydra_engine.wiki.sidecar_entries import SidecarEntry, SidecarParseError, read_sidecar_entries


def _valid_checked_on(value: str) -> bool:
    if not value:
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value


def _remediation(
    entry: SidecarEntry,
    sidecar: str,
    source: str,
    category: str,
    *,
    deleted: bool = False,
) -> str | None:
    if category == "no-declared-sources":
        return None
    if category == "not-one-existing-file":
        if deleted:
            return (
                f"edit {sidecar} objects.{entry.name}.provenance.sources to drop or repoint "
                f"'{source}'"
            )
        return (
            "wiki fingerprint cannot fix this; edit "
            f"{sidecar} objects.{entry.name}.provenance.sources to drop or repoint "
            f"'{source}', then: hydra.py wiki fingerprint --page {entry.hydra_id}"
        )
    return (
        "re-verify the page against its sources, then: "
        f"hydra.py wiki fingerprint --page {entry.hydra_id}"
    )


def _finding(
    entry: SidecarEntry,
    sidecar: str,
    category: str,
    source: str = "",
    *,
    deleted: bool = False,
) -> dict[str, object]:
    if category == "digest-mismatch":
        detail = f"digest mismatch: {source}"
    elif category == "committed-after-checked-on":
        detail = f"{source} committed after checked_on"
    elif category == "not-one-existing-file":
        detail = (
            f"{source} was deleted in this commit; {entry.hydra_id} still declares it"
            if deleted
            else f"source is not one existing file: {source}"
        )
    elif category == "no-declared-sources":
        detail = "no declared sources"
    else:
        detail = "cannot assess because checked_on is absent or invalid"
    return {
        "category": category,
        "source": source or None,
        "detail": detail,
        "remediation": _remediation(entry, sidecar, source, category, deleted=deleted),
    }


def _page_report(
    entry: SidecarEntry,
    sidecar: Path,
    paths: ContextCompilerPaths,
    changed_paths: set[str] | None = None,
) -> dict[str, object]:
    findings: list[dict[str, object]] = []
    sidecar_display = display_path(sidecar, paths.root)
    sources = entry.sources
    if not sources:
        findings.append(_finding(entry, sidecar_display, "no-declared-sources"))
    else:
        valid_date = _valid_checked_on(entry.checked_on)
        if not valid_date:
            findings.append(_finding(entry, sidecar_display, "cannot-assess-checked-on"))
        missing = []
        for source in sources:
            source_path = resolve_source_path(source, paths)
            if not source_path.is_file():
                missing.append((source, changed_paths is not None and source in changed_paths and not source_path.exists()))
        findings.extend(
            _finding(entry, sidecar_display, "not-one-existing-file", source, deleted=deleted)
            for source, deleted in missing
        )
        if valid_date:
            stale = stale_provenance_sources(
                entry.provenance,
                checked_on=entry.checked_on,
                paths=paths,
            )
            digest_sources = {item["source"] for item in entry.source_digests}
            for source in stale:
                category = "digest-mismatch" if source in digest_sources else "committed-after-checked-on"
                findings.append(_finding(entry, sidecar_display, category, source))
    return {
        "name": entry.name,
        "hydra_id": entry.hydra_id,
        "path": entry.path,
        "checked_on": entry.checked_on,
        "sources": sources,
        "source_digests": entry.source_digests,
        "status": "clean" if not findings else "finding",
        "findings": findings,
    }


def _sidecar_paths(args, paths: ContextCompilerPaths) -> list[Path]:
    root = paths.hydra / "surfaces/wiki"
    if args.wiki:
        return [root / f"{args.wiki}.yaml"] if (root / f"{args.wiki}.yaml").is_file() else []
    return sorted(root.glob("*.yaml"))


def audit_report(args, paths: ContextCompilerPaths) -> dict[str, object]:
    changed_in = getattr(args, "changed_in", "") or ""
    changed_paths = set(git_port.commit_changed_paths(paths.root, changed_in)) if changed_in else None
    sidecars: list[dict[str, object]] = []
    for sidecar in _sidecar_paths(args, paths):
        display = display_path(sidecar, paths.root)
        try:
            entries = read_sidecar_entries(sidecar, paths.root)
        except (OSError, UnicodeError, SidecarParseError, ValueError) as error:
            sidecars.append({"name": sidecar.stem, "path": display, "status": "unreadable", "error": str(error), "pages": []})
            continue
        if changed_paths is not None:
            entries = [entry for entry in entries if changed_paths.intersection(entry.sources)]
        sidecars.append({
            "name": sidecar.stem,
            "path": display,
            "status": "ok",
            "pages": [_page_report(entry, sidecar, paths, changed_paths) for entry in entries],
        })
    pages = [page for sidecar in sidecars for page in sidecar["pages"]]
    findings = [finding for page in pages for finding in page["findings"]]
    stale_categories = {"digest-mismatch", "committed-after-checked-on"}
    return {
        "sidecars": sidecars,
        "summary": {
            "sidecars": len(sidecars),
            "pages": len(pages),
            "stale_pages": sum(
                any(finding["category"] in stale_categories for finding in page["findings"])
                for page in pages
            ),
            "no_source_pages": sum(
                any(finding["category"] == "no-declared-sources" for finding in page["findings"])
                for page in pages
            ),
            "unverifiable_pages": sum(
                any(finding["category"] == "cannot-assess-checked-on" for finding in page["findings"])
                for page in pages
            ),
            "finding_pages": sum(page["status"] == "finding" for page in pages),
            "findings": len(findings),
            "unreadable_sidecars": sum(sidecar["status"] == "unreadable" for sidecar in sidecars),
        },
    }


def _print_report(report: dict[str, object], paths: ContextCompilerPaths, wiki_name: str = "") -> None:
    print("Hydra wiki audit")
    sidecars = report["sidecars"]
    if not sidecars:
        target = f"{wiki_name}.yaml" if wiki_name else "*.yaml"
        print(f"- no sidecar found: {paths.hydra.relative_to(paths.root)}/surfaces/wiki/{target}")
    for sidecar in sidecars:
        path = sidecar["path"]
        if sidecar["status"] == "unreadable":
            print(f"- sidecar-unreadable: {path}: {sidecar['error']}")
            continue
        print(f"- sidecar: {path}")
        for page in sidecar["pages"]:
            print(f"  - {page['hydra_id']} ({page['path']}): {page['status']}")
            for finding in page["findings"]:
                source = f" [{finding['source']}]" if finding["source"] else ""
                print(f"    - {finding['detail']}{source}")
                if finding["remediation"]:
                    print(f"      {finding['remediation']}")
    summary = report["summary"]
    print(
        f"Summary: {summary['pages']} page(s), {summary['stale_pages']} stale page(s), "
        f"{summary['findings']} finding(s)"
    )


def command_wiki_audit(args, paths: ContextCompilerPaths) -> CommandResult:
    report = audit_report(args, paths)
    if getattr(args, "changed_in", "") and not report["summary"]["pages"]:
        return CommandResult(0)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report, paths, args.wiki or "")
    return CommandResult(0)
