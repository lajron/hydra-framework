"""Knowledge-node Markdown/unit validation and optional Graphviz
diagram rendering.

Unit `reads:` validation uses `documents.tokens.cited_source_path_missing` for
the same brace-set/glob/trailing-slash heuristic object provenance and flat
knowledge use. Path citation resolution is intentionally shared so validators
do not grow separate ideas of what a repository-relative source path means.
"""

from __future__ import annotations

import shutil
import subprocess
import re
from pathlib import Path

from hydra_engine.documents.tokens import cited_source_path_missing, read_text
from hydra_engine.finding import Finding
from hydra_engine.identity.hydra_ids import HYDRA_ID_RE
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN, approx_tokens
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.knowledge.units import (
    UNIT_KINDS,
    discover_unit_paths,
    non_unit_reason,
    read_unit,
    required_closure,
)
from hydra_engine.wiki.links import validate_markdown_links

QUESTION_MAX_LENGTH = 120
SOURCE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# A deliberately generous tripwire against an accidental
# oversized dump, not a tuned optimum -- derived from this repository's own
# `compile-context --budget` default (12000 approx tokens) rather than
# imported from another repository's evidence corpus. Revisit once it first
# fires against real content. Named "package file", not "slice" or "unit":
# it scans every Markdown file under a package root regardless of registered
# `kind` (`knowledge-package`'s own `overview.md`, `knowledge-slice` envelopes
# like `state.md`/`problems.md`, and `knowledge-unit` files under `units/`
# alike), so a kind-specific name would misstate its scope.  The exported
# constant retains its historical spelling as a CLI-policy compatibility key.
PACKAGE_FILE_FAIL_TOKENS = 8000


def validate_unit_source_digests(unit, rel: str, paths: ContextCompilerPaths) -> list[Finding]:
    findings: list[Finding] = []
    entries = unit.source_digests
    if entries in (None, "", ()):
        return findings
    if not isinstance(entries, list):
        return [Finding(
            path=rel,
            code="unit-source-digest",
            detail=f"{rel}: `provenance.source_digests` must be a list of mappings",
        )]

    seen: set[str] = set()
    sources = set(unit.sources)
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            findings.append(Finding(
                path=rel,
                code="unit-source-digest",
                detail=f"{rel}: `provenance.source_digests[{index}]` must be a mapping",
            ))
            continue
        source_value = entry.get("source")
        digest_value = entry.get("digest")
        source = source_value if isinstance(source_value, str) else ""
        digest = digest_value if isinstance(digest_value, str) else ""
        if not source or not digest:
            findings.append(Finding(
                path=rel,
                code="unit-source-digest",
                detail=f"{rel}: `provenance.source_digests[{index}]` requires `source` and `digest`",
            ))
            continue
        if not SOURCE_DIGEST_RE.match(digest):
            findings.append(Finding(
                path=rel,
                code="unit-source-digest",
                detail=f"{rel}: `provenance.source_digests[{index}].digest` must match sha256:<64 hex>",
            ))
        if source not in sources:
            findings.append(Finding(
                path=rel,
                code="unit-source-digest",
                detail=f"{rel}: `provenance.source_digests[{index}].source` is not listed in `provenance.sources`: {source}",
            ))
        if source in seen:
            findings.append(Finding(
                path=rel,
                code="unit-source-digest",
                detail=f"{rel}: duplicate `provenance.source_digests` source: {source}",
            ))
        seen.add(source)
        if unit.certainty != "unresolved":
            path = Path(source)
            if not path.is_absolute():
                path = paths.root / source
            if not path.is_file():
                findings.append(Finding(
                    path=rel,
                    code="unit-source-digest",
                    detail=f"{rel}: `provenance.source_digests[{index}].source` does not resolve to one existing file: {source}",
                ))
    return findings


def render_dot_diagrams(root: Path, repo_root: Path) -> list[str]:
    """Not part of the validate_* family: a rendering side effect (writes
    `images/*.svg`/`*.png`), not a check, so it stays `list[str]` -- only
    the validator family converts to `Finding`."""
    errors: list[str] = []
    dots = sorted((root / "diagrams").glob("*.dot"))
    if not dots:
        return errors
    if shutil.which("dot") is None:
        print("Diagram render skipped: Graphviz `dot` not found.")
        return errors
    images = root / "images"
    images.mkdir(exist_ok=True)
    for dot_file in dots:
        stem = dot_file.stem
        for fmt in ["svg", "png"]:
            out = images / f"{stem}.{fmt}"
            result = subprocess.run(["dot", f"-T{fmt}", str(dot_file), "-o", str(out)], capture_output=True, text=True)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                errors.append(f"render failed: {dot_file.relative_to(repo_root)} as {fmt}: {detail}")
            else:
                print(f"rendered: {out.relative_to(repo_root)}")
    return errors


def validate_units_dir(root: Path, paths: ContextCompilerPaths, resolver_paths: ObjectLocations) -> list[Finding]:
    """Validate a package's `units/` directory.

    Existence resolution of a `requires`/`see_also`/`expand_when[].read`
    `hydra://` id is not this function's job: those ids are plain text in a
    Markdown file, so `ref check`'s existing whole-tree reference scan
    (`objects.references`, via `identity.hydra_ids.hydra_refs_in_text`)
    already resolves them the same way it resolves any other `hydra://`
    mention. This function only asserts the id *shape*, per the design
    note's own division of labor.

    Staleness (comparing a cited source's last commit against `checked_on`)
    is deliberately not checked here: every `Finding` this function returns
    makes `validate` exit nonzero (see `commands.validation.command_validate`
    -- there is no separate warning tier), which would turn an intentionally
    stale unit into a hard failure. That contradicts the design's own "never
    a hard failure" requirement for staleness, so it is surfaced instead as a
    `compile-context` candidate annotation (`knowledge.candidates.unit_candidates`),
    which is advisory by construction.
    """
    findings: list[Finding] = []
    units_map: dict = {}
    parsed: list[tuple[Path, object]] = []

    for path in discover_unit_paths(root):
        rel = str(path.relative_to(paths.root))
        unit = read_unit(path, paths.root)
        if unit is None:
            reason = non_unit_reason(path, paths.root)
            findings.append(Finding(
                path=rel, code="unit-not-recognized",
                detail=f"{rel}: {reason} -- invisible to compile-context and ref check as a unit",
            ))
            continue
        parsed.append((path, unit))
        if unit.hydra_id:
            units_map[unit.hydra_id] = unit

    for path, unit in parsed:
        rel = str(path.relative_to(paths.root))

        if unit.unit_kind not in UNIT_KINDS:
            findings.append(Finding(
                path=rel, code="unit-kind",
                detail=f"{rel}: unit_kind `{unit.unit_kind}` is not one of {UNIT_KINDS}",
            ))

        question = unit.question
        if not question:
            findings.append(Finding(path=rel, code="unit-question", detail=f"{rel}: missing `question`"))
        else:
            if not question.endswith("?"):
                findings.append(Finding(path=rel, code="unit-question", detail=f"{rel}: `question` must end with `?`"))
            if len(question) > QUESTION_MAX_LENGTH:
                findings.append(Finding(
                    path=rel, code="unit-question",
                    detail=f"{rel}: `question` exceeds {QUESTION_MAX_LENGTH} characters",
                ))
            if " and " in question.lower():
                findings.append(Finding(
                    path=rel, code="unit-question",
                    detail=f"{rel}: `question` contains \"and\" - likely two units, not one (warning, not blocked)",
                ))

        if unit.unit_kind == "rule" and not unit.sources:
            findings.append(Finding(
                path=rel, code="unit-rule-sources",
                detail=f"{rel}: unit_kind `rule` requires a non-empty `provenance.sources`",
            ))
        findings.extend(validate_unit_source_digests(unit, rel, paths))
        if unit.unit_kind == "status" and not unit.checked_on:
            findings.append(Finding(
                path=rel, code="unit-status-checked-on",
                detail=f"{rel}: unit_kind `status` requires `checked_on`",
            ))
        if unit.unit_kind == "divergence":
            if unit.certainty != "conflicting":
                findings.append(Finding(
                    path=rel, code="unit-divergence-certainty",
                    detail=f"{rel}: unit_kind `divergence` requires `certainty: conflicting`",
                ))
            if "effect on agents" not in read_text(path).lower():
                findings.append(Finding(
                    path=rel, code="unit-divergence-effect",
                    detail=f"{rel}: unit_kind `divergence` must name the effect on agents",
                ))

        # `certainty: unresolved` is the vocabulary-collapse successor to the
        # deleted context-pack `PLANNED` substring exemption: a unit
        # legitimately naming an unshipped path must not fail
        # validation for citing it.
        if unit.certainty != "unresolved":
            for raw in unit.reads:
                if cited_source_path_missing(raw, path.parent, paths.root):
                    findings.append(Finding(
                        path=rel, code="unit-read-path",
                        detail=f"{rel}: `reads:` path does not exist: {raw}",
                    ))

        for label, refs in [("requires", unit.requires), ("see_also", unit.see_also)]:
            for ref in refs:
                if not HYDRA_ID_RE.match(ref):
                    findings.append(Finding(
                        path=rel, code="unit-ref-shape",
                        detail=f"{rel}: `{label}` entry is not a valid hydra:// id: {ref}",
                    ))
        for entry in unit.expand_when:
            read_refs = entry.get("read")
            for ref in read_refs if isinstance(read_refs, list) else []:
                if not HYDRA_ID_RE.match(ref):
                    findings.append(Finding(
                        path=rel, code="unit-ref-shape",
                        detail=f"{rel}: `expand_when[].read` entry is not a valid hydra:// id: {ref}",
                    ))

        if unit.hydra_id:
            cycle_warnings: list[str] = []
            required_closure(units_map, {unit.hydra_id}, cycle_warnings)
            findings.extend(Finding(path=rel, code="unit-requires-cycle", detail=f"{rel}: {w}") for w in cycle_warnings)

    return findings


def validate_package_file_sizes(
    root: Path,
    paths: ContextCompilerPaths,
    fail_tokens: int = PACKAGE_FILE_FAIL_TOKENS,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> list[Finding]:
    """Hard-ceiling backstop against an oversized knowledge-package file --
    any Markdown file under a package root, deliberately not scoped to one
    registered `kind`. Deliberately has no companion warning
    tier: this repository has no legitimate content anywhere near the
    ceiling yet, so a non-failing advisory would have nothing real to advise
    about. Add one when a genuine large-but-legitimate file shows up (the
    summary-first half of this backstop), not before.
    """
    findings: list[Finding] = []
    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        tokens = approx_tokens(read_text(path), chars_per_token)
        if tokens > fail_tokens:
            rel = str(path.relative_to(paths.root))
            findings.append(Finding(
                path=rel, code="package-file-size",
                detail=f"{rel}: {tokens} approx tokens exceeds the {fail_tokens}-token hard ceiling",
            ))
    return findings


def validate_package_root(
    root: Path,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    render: bool = False,
    command_ids: tuple[str, ...] = (),
    file_fail_tokens: int = PACKAGE_FILE_FAIL_TOKENS,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
) -> list[Finding]:
    if not root.exists() or not root.is_dir():
        return [Finding(path=str(root), code="package-root", detail=f"package path is not a directory: {root}")]
    findings: list[Finding] = []
    findings.extend(validate_markdown_links(root, paths.root))
    findings.extend(validate_units_dir(root, paths, resolver_paths))
    findings.extend(validate_package_file_sizes(root, paths, file_fail_tokens, chars_per_token))
    if render:
        findings.extend(
            Finding(path=str(root), code="package-root", detail=detail)
            for detail in render_dot_diagrams(root, paths.root)
        )
    return findings
