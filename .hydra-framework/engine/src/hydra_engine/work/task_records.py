"""Personal task record parsing, summaries, and hygiene notes.

`validate_task_file` takes `required_sections` as a plain argument rather
than importing a constant: `scripts/hydra.py`'s `REQUIRED_TASK_SECTIONS` is
also read directly by `validate_task_contract_docs`, so it stays defined
in the shim and is passed in rather than duplicated or aliased.
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

from hydra_engine.documents.tokens import display_path, is_relative_to, read_text, write_text
from hydra_engine.finding import Finding
from hydra_engine.identity.slugs import slugify
from hydra_engine.ports import clock, fs, git

STALE_TASK_DAYS = 14
from hydra_engine.work.paths import WorkPaths

TASK_OUTCOME_FORBIDDEN_PREFIXES = (
    ".git/",
    ".hydra-framework.local/",
    ".hydra-framework/intake/raw/",
    ".hydra-framework/intake/extracted/",
    ".hydra-framework/intake/triage/",
    ".hydra-framework/tasks/personal/",
    ".hydra-framework/tasks/templates/",
)


def task_header_field(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:[ \t]*(.*)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def task_bullet_field(text: str, label: str) -> str:
    match = re.search(rf"^[ \t]*-[ \t]+{re.escape(label)}:[ \t]*(.*)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def task_bullet_field_is_none(text: str, label: str) -> bool:
    value = task_bullet_field(text, label).lower()
    return bool(re.match(r"^none(?:\.(?:[ \t].*)?|$)", value))


def task_name_from_path(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
    return slugify(stem)


def resolve_task_record(value: str, paths: WorkPaths, caller_owner: str) -> tuple[Path | None, list[str]]:
    """Resolve the documented task `<name-or-path>` argument.

    Path-shaped arguments retain exact path semantics. Bare names prefer one
    caller-owned record before falling back to one unambiguous global match.
    """
    raw = value.strip()
    candidate = Path(raw)
    explicit_path = candidate.is_absolute() or len(candidate.parts) > 1 or candidate.suffix == ".md"
    if explicit_path:
        resolved = candidate if candidate.is_absolute() else paths.root / candidate
        if resolved.exists():
            return resolved, []
        return None, [f"Task not found: {resolved}"]

    slug = slugify(raw)
    matches = [path for path in iter_personal_task_files(paths) if task_name_from_path(path) == slug]
    owner_matches = [path for path in matches if personal_task_owner(path, paths) == caller_owner]
    preferred = owner_matches if owner_matches else matches
    if len(preferred) == 1:
        return preferred[0], []
    if len(preferred) > 1:
        return None, [
            f"Task name is ambiguous: {raw}",
            *(f"- {display_path(path, paths.root)}" for path in preferred),
            "Use an explicit task record path.",
        ]
    return None, [f"Task not found: {paths.root / candidate}"]


def task_state_git_path(path: Path, paths: WorkPaths) -> str:
    return display_path(path, paths.root)


def personal_task_owner(path: Path, paths: WorkPaths) -> str:
    """Return the owner directory for a personal task record path."""
    root = paths.personal_tasks_root()
    if not is_relative_to(path, root):
        return ""
    relative = path.relative_to(root)
    if len(relative.parts) < 2 or relative.parts[1] == "checkpoints":
        return ""
    return relative.parts[0]


def task_owner_write_refusal_lines(task: Path, paths: WorkPaths, caller_owner: str, force: bool) -> list[str]:
    record_owner = personal_task_owner(task, paths)
    if not record_owner:
        return [f"Task is not a personal task record: {display_path(task, paths.root)}"]
    if record_owner == caller_owner or force:
        return []
    return [
        f"Refusing to edit {record_owner}'s task as {caller_owner}: {display_path(task, paths.root)}",
        "Re-run with --force only if you are deliberately overriding task ownership.",
    ]


def stage_task_state_file(path: Path, paths: WorkPaths) -> bool:
    return git.stage_file(paths.root, task_state_git_path(path, paths))


def stage_task_state_files(paths: WorkPaths, files: list[Path]) -> list[str]:
    return [
        task_state_git_path(path, paths)
        for path in files
        if not stage_task_state_file(path, paths)
    ]


def task_completion_staging_lines(paths: WorkPaths, files: list[Path]) -> list[str]:
    failures = stage_task_state_files(paths, files)
    if not failures:
        return ["Staged completed task deletion for Git."]

    lines = ["Task completion deletion is not fully staged for Git:"]
    lines.extend(f"- {rel}" for rel in failures)
    lines.append("Stage the deletion before committing.")
    return lines


def task_completion_git_status_lines(paths: WorkPaths) -> list[str]:
    status = git.short_status(paths.root)
    if not status:
        return ["Git status: clean."]

    lines = ["Git status after completion:"]
    lines.extend(f"  {line}" for line in status[:20])
    if len(status) > 20:
        lines.append(f"  ... {len(status) - 20} more")
    lines.append("Next: review `git status`, then commit.")
    return lines


def write_new_state_file(path: Path, content: str, *, force: bool = False) -> bool:
    """Create `path` with `content`, refusing to clobber an existing file
    unless `force`. Returns False without writing anything when refused.

    The exists-check and the write are a single atomic OS operation when not
    forcing, closing the TOCTOU window two racing callers used to have.
    """
    if force:
        write_text(path, content)
        return True
    return fs.create_exclusive(path, content)


def append_state_line(path: Path, line: str) -> None:
    """Append one line to a private-tier state file with no read-modify-
    write (same amendment): two concurrent appenders can only ever add a
    line, never lose one another's."""
    fs.append_line(path, line)


def unrecoverable_task_state_paths(paths: WorkPaths, files: list[Path]) -> list[tuple[str, str]]:
    problems = []
    for path in files:
        rel = task_state_git_path(path, paths)
        if not git.is_tracked(paths.root, rel):
            problems.append((rel, "not tracked by Git"))
        elif not git.worktree_matches_index(paths.root, rel):
            problems.append((rel, "has unstaged changes Git cannot recover"))
    return problems


def task_outcome_refusal_lines(outcome: str, paths: WorkPaths) -> list[str]:
    """Validate the mechanical `task complete --outcome` contract.

    The command cannot prove that a file contains durable meaning, but it can
    refuse paths that are not recoverable shared/source artifacts at all.
    """
    raw = outcome.strip()
    if not raw:
        return ["Outcome is empty."]
    candidate = Path(raw)
    if candidate.is_absolute():
        return [f"Outcome must be a repository-relative path: {raw}"]

    target = (paths.root / candidate).resolve()
    if not is_relative_to(target, paths.root):
        return [f"Outcome must stay inside this repository: {raw}"]
    if not target.exists():
        return [f"Outcome does not exist: {raw}"]
    if not target.is_file():
        return [f"Outcome is not a file: {raw}"]

    rel = display_path(target, paths.root)
    for prefix in TASK_OUTCOME_FORBIDDEN_PREFIXES:
        if rel.startswith(prefix):
            return [f"Outcome is not a durable shared/source artifact: {rel}"]
    return []


def task_summary(path: Path, root: Path) -> dict[str, str]:
    """One-line view of a task record, computed from the record itself.

    Nothing stores this. A separate status file would be a second index that can
    disagree with the records, and this repository has already been bitten by
    derived state that nothing forces to stay true.
    """
    text = read_text(path)
    owner = path.parent.name
    if owner == "checkpoints":
        owner = path.parent.parent.name
    goal = ""
    for line in text.partition("## Goal")[2].splitlines():
        if line.strip():
            goal = line.strip()
            break
    return {
        "owner": owner,
        "path": display_path(path, root),
        "name": task_name_from_path(path),
        "status": task_header_field(text, "Status") or "unknown",
        "updated": task_header_field(text, "Updated") or task_header_field(text, "Created"),
        "goal": goal,
    }


def set_task_status(content: str, status: str) -> str:
    """Rewrite the leading `Status:` header of a task record.

    Only the header is touched. Later `Status:` lines belong to nested blocks
    such as readiness, which have their own vocabulary.
    """
    return re.sub(
        r"^Status:.*$", f"Status: {status}", content, count=1, flags=re.MULTILINE
    )


def touch_task_updated(content: str) -> str:
    """Refresh the record's `Updated:` header.

    The board and the staleness check both read this field, so any command that
    changes a record must move it. A record whose date lies is worse than one
    with no date, because it reads as confirmed-current.
    """
    if re.search(r"^Updated:", content, flags=re.MULTILINE):
        return re.sub(r"^Updated:.*$", f"Updated: {clock.today()}", content, count=1, flags=re.MULTILINE)
    return re.sub(
        r"^(Status:.*)$", rf"\1\nUpdated: {clock.today()}", content, count=1, flags=re.MULTILINE
    )


def validate_task_file(path: Path, required_sections: list[str], root: Path) -> list[Finding]:
    """Every required label must appear somewhere in the record's text.

    `root` is only for display: the missing-section messages used to be built
    by `command_validate` itself (`f"{display_path(task_path)} missing ..."`)
    over this function's raw missing-section names; the Finding conversion
    moves that formatting in here so the
    message text stays byte-identical while the caller stops needing to know
    this validator's message shape.
    """
    text = read_text(path)
    label = display_path(path, root)
    return [
        Finding(path=label, code="task-file", detail=f"{label} missing `{item}`")
        for item in required_sections
        if item not in text
    ]


def validate_personal_task_file(path: Path, root: Path) -> list[Finding]:
    """Semantic checks for per-owner task records.

    `validate_task_file` only proves required labels exist. Owner attribution is
    a path contract: if the header and directory disagree, `board` and a human
    reader answer "who owns this?" differently.
    """
    text = read_text(path)
    owner = task_header_field(text, "Owner")
    if owner and owner != path.parent.name:
        label = display_path(path, root)
        return [Finding(
            path=label, code="personal-task-file",
            detail=f"{label} Owner `{owner}` does not match directory `{path.parent.name}`",
        )]
    return []


def iter_personal_task_files(paths: WorkPaths) -> list[Path]:
    """Every tracked active task record, across all owners."""
    root = paths.personal_tasks_root()
    if not root.is_dir():
        return []
    return sorted(root.glob("*/*.md"))


def iter_personal_checkpoints(paths: WorkPaths) -> list[Path]:
    root = paths.personal_tasks_root()
    if not root.is_dir():
        return []
    return sorted(root.glob("*/checkpoints/*.md"))


def duplicate_task_slug_findings(paths: WorkPaths) -> list[Finding]:
    """Cross-owner duplicate-work detection.

    One person hitting the same slug twice is a rename or a resumed task;
    two different owners filing the same slug is two people doing the same
    work without knowing it, the exact aggregation blindness placement-rules'
    shared-queue tests warn about. Cheap and explainable, like the flat-
    knowledge duplicate-title check: exact slug match only, no semantic
    overlap detection.
    """
    by_slug: dict[str, list[Path]] = {}
    for path in iter_personal_task_files(paths):
        by_slug.setdefault(task_name_from_path(path), []).append(path)

    findings: list[Finding] = []
    for slug, task_paths in by_slug.items():
        owners_for_slug = {path.parent.name for path in task_paths}
        if len(owners_for_slug) > 1:
            joined = ", ".join(display_path(path, paths.root) for path in task_paths)
            findings.append(Finding(
                path="", code="duplicate-task-work",
                detail=(
                    f"task slug `{slug}` is active under more than one owner: {joined}; "
                    "if this is a `task handoff` interrupted partway, rerun it to finish moving "
                    "the record, otherwise resolve which owner's copy is current by hand"
                ),
            ))
    return findings


def personal_task_notes(paths: WorkPaths, stale_days: int = STALE_TASK_DAYS) -> list[str]:
    """Advisory observations about tracked task records.

    These are notes, not errors. A stale record is a prompt to update it, not a
    reason to fail someone's build -- and a check that blocks work for bookkeeping
    is a check people route around.
    """
    notes: list[str] = []
    cutoff = _dt.date.fromisoformat(clock.today()) - _dt.timedelta(days=stale_days)
    for path in iter_personal_task_files(paths):
        summary = task_summary(path, paths.root)
        if summary["status"] not in {"active", "blocked", "parked"}:
            notes.append(f"{summary['path']}: status `{summary['status']}` in the active tier")
        text = read_text(path)
        readiness_status = task_bullet_field(text, "Status").lower()
        if (
            summary["status"] == "active"
            and readiness_status == "ready"
            and task_bullet_field_is_none(text, "Active step")
        ):
            notes.append(
                f"{summary['path']}: active task has `Active step: none`; "
                "complete it or set the active step"
            )
        if summary["status"] == "blocked" and task_bullet_field_is_none(text, "Blockers and assumptions"):
            notes.append(
                f"{summary['path']}: blocked task has `Blockers and assumptions: none`; "
                "record the blocker or change the status"
            )
        updated = summary["updated"]
        try:
            if updated and _dt.date.fromisoformat(updated) < cutoff:
                notes.append(f"{summary['path']}: not updated since {updated}")
        except ValueError:
            notes.append(f"{summary['path']}: `Updated:` is not a YYYY-MM-DD date")
    return notes


def prune_empty_owner_dir(owner_dir: Path, paths: WorkPaths) -> None:
    """Drop an owner directory once their last record leaves.

    Git does not track empty directories, so this only affects the working tree --
    but a directory per former owner reads as "they have work in flight" to
    anyone listing the tree, which is the exact ambiguity the tiers exist to fix.
    """
    if not owner_dir.is_dir() or not is_relative_to(owner_dir, paths.personal_tasks_root()):
        return
    checkpoints = owner_dir / "checkpoints"
    if checkpoints.is_dir() and not any(checkpoints.iterdir()):
        checkpoints.rmdir()
    if not any(owner_dir.iterdir()):
        owner_dir.rmdir()
