"""Shared fixture content and golden-assertion helpers.

Every golden test in this package builds a small synthetic Hydra tree via
`harness.run_command`'s `fixture=` dict — never a clone of the live
repository — so a golden only changes when the command's own logic changes,
not when someone edits `AI_SYSTEM.md` next week. `BASE_FIXTURE` is the
minimal tree that satisfies `REQUIRED_PATHS` (see `scripts/hydra.py`); most
goldens layer a few extra files on top of it.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from ..harness import CommandOutcome, recording_enabled, run_command
from hydra_engine import thresholds

GOLDENS_DATA_DIR = Path(__file__).resolve().parent / "data"

FROZEN_TODAY = "2026-01-01"
FROZEN_UTC_ISO = "2026-01-01T00:00:00Z"
FROZEN_LOCAL_ISO = "2026-01-01T00:00:00"
FROZEN_STAMP = "20260101-000000"
FROZEN_UID = "00000000-0000-0000-0000-000000000000"

# The real templates' exact text: `command_task_start`/`command_task_checkpoint`
# do substring replacement on these, so a placeholder would silently no-op.
TASK_TEMPLATE = """# Task: <short-name>

Status: active
Owner: unassigned
Created: YYYY-MM-DD
Updated: YYYY-MM-DD

## Goal

Describe the engineering objective.

## Confirmed Decisions

- None yet.

## Approved Plan

- None yet.

## Current Stage

Not started.

## Readiness

Status: not-checked

- Branch or workspace assumptions:
- Relevant canonical docs:
- Required dependencies, services, generated artifacts, or private local requirements:
- Blockers and assumptions:
- Expected validation command or evidence:

## Step State

- Active step: none
- Next step: none
- Completed steps: none
- Superseded or skipped steps: none

## Changed Files

- None yet.

## Validation

- None yet.

## Blockers

- None.

## Continuation Notes

What another model or developer needs to continue safely.

- Running state: none
- Resume check: none
"""

CHECKPOINT_TEMPLATE = """# Checkpoint: <task-name>

Task: <link-or-name>
Created: YYYY-MM-DD
Status: paused

## Goal

## Confirmed Decisions

## Approved Plan

## Completed Work

## Current Stage

## Changed Files

## Validation Performed

## Remaining Work

## Blockers

## Useful References

## Continuation Prompt

Start by reading `AI_SYSTEM.md`, this checkpoint, and the referenced task state. Continue from the current stage without relying on prior conversation history.
"""

CAPABILITY_CALLERS_FIXTURE = """schema: hydra-framework.capability-callers.v1
mechanisms:
  fixture:
    classification: manual
    implementation:
      .hydra-framework/validation/capability-callers.yaml:
        - fixture
    callers:
      .hydra-framework/validation/capability-callers.yaml:
        - manual
"""

PRIVATE_TIER_SHAPE_FIXTURE = """---
title: State Tiers
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources: []
---
# State Tiers

## Private Tier Shape

| Path | Kind | Holds |
| --- | --- | --- |
| `notes/` | machine | fixture |
| `intake/raw/` | machine | fixture |
| `intake/extracted/` | machine | fixture |
| `intake/triage/` | machine | fixture |
| `monitoring/` | machine | fixture |
| `index/` | machine | fixture |
| `logs/` | machine | fixture |
| `baseline/` | machine | fixture |
| `tasks/retired/` | machine | fixture |
| `migrations/` | machine | fixture |
| `evolution/experiments/` | machine | fixture |
| `scratch/` | thinking | fixture |
| `plans/` | thinking | fixture |
| `research/` | thinking | fixture |
| `prompts/` | thinking | fixture |
| `diagrams/` | thinking | fixture |
| `source-material/` | thinking | fixture |
| `tickets/` | thinking | fixture |
| `bug-reports/` | thinking | fixture |
| `developer/` | config | fixture |
| `machine/` | config | fixture |
| `repo-overrides/` | config | fixture |
| `secrets/` | config | fixture |
"""


def engine_policy_fixture() -> str:
    lines = ["schema: hydra-framework.engine-policy.v1", "thresholds:"]
    for entry in thresholds.THRESHOLDS:
        if entry.classification == thresholds.TEAM_TUNABLE_POLICY:
            lines.append(f"  {entry.key}: {entry.value}")
    return "\n".join(lines) + "\n"


DELEGATION_POLICY_FIXTURE = """schema: hydra-framework.delegation-policy.v1
enabled: true
max_active_workers: 2
max_depth: 1
allowed_reasons:
  - inspection
  - implementation-support
  - review
  - validation
  - summarization
role_defaults:
  allowed_capability_classes:
    - fast-default
    - cheap-triage
    - deep-reasoning
    - large-context
    - tool-heavy
    - review-focused
    - local-private
  fallback_capability_class: fast-default
  effort_ceiling: max
roles: {}
"""


# Distinct from FROZEN_UID so a space fixture never collides with the
# duplicate-uid case in the every-validator-fails golden.
KNOWLEDGE_SPACE_UID = "00000000-0000-0000-0000-0000000000aa"

KNOWLEDGE_SPACES_FIXTURE = (
    "schema: hydra-framework.knowledge-spaces.v1\n"
    "default_depth: 3\n"
    "max_depth: 4\n"
    "spaces:\n"
    "  - demo\n"
)


def knowledge_space_fixture(
    *,
    space: str = "demo",
    overview: str = "# Demo\n",
    space_doc: str | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """One valid Knowledge v3 space, or a deliberately broken one.

    `space_doc` replaces the node document so a negative golden can exercise
    the node contract; `overview`/`extra` supply owned content.
    """
    root = f".hydra-framework/repo/knowledge/spaces/{space}"
    default_doc = (
        "schema: hydra-framework.knowledge-node.v1\n"
        f"node: {space}\n"
        f"hydra_id: hydra://knowledge-space/{space}\n"
        f"uid: {KNOWLEDGE_SPACE_UID}\n"
        "schema_version: 3\n"
        "kind: knowledge-space\n"
        f"title: {space.title()}\n"
        "status: active\n"
        "scope: repo-local\n"
        "owners:\n"
        "  team: fixture-owners\n"
        "relations: []\n"
        "provenance:\n"
        "  sources: []\n"
        "routable: true\n"
        "state: ./state.md\n"
        "overview: ./overview.md\n"
        "keywords: []\n"
    )
    fixture = {
        ".hydra-framework/repo/knowledge/spaces.yaml": KNOWLEDGE_SPACES_FIXTURE,
        f"{root}/space.yaml": default_doc if space_doc is None else space_doc,
        f"{root}/state.md": f"# {space} state\n",
        f"{root}/overview.md": overview,
    }
    fixture.update(extra or {})
    return fixture



SPACE_DOC_WITH_ROUTE = (
    "schema: hydra-framework.knowledge-node.v1\n"
    "node: demo\n"
    "hydra_id: hydra://knowledge-space/demo\n"
    f"uid: {KNOWLEDGE_SPACE_UID}\n"
    "schema_version: 3\n"
    "kind: knowledge-space\n"
    "title: Demo\n"
    "status: active\n"
    "scope: repo-local\n"
    "owners:\n"
    "  team: fixture-owners\n"
    "relations: []\n"
    "provenance:\n"
    "  sources: []\n"
    "routable: true\n"
    "state: ./state.md\n"
    "overview: ./overview.md\n"
    "keywords:\n"
    "  - demo\n"
    "  - routing\n"
    "routes:\n"
    "  demo_task:\n"
    "    use_when:\n"
    "      - handle a demo routing task\n"
    "    priority_units:\n"
    "      - hydra://knowledge-unit/demo/guide\n"
)

DEMO_UNIT = (
    "---\n"
    "hydra_id: hydra://knowledge-unit/demo/guide\n"
    "uid: 00000000-0000-0000-0000-0000000000bb\n"
    "schema_version: 3\n"
    "kind: knowledge-unit\n"
    "title: Demo Guide\n"
    "status: active\n"
    "scope: repo-local\n"
    "owners:\n"
    "  team: fixture-owners\n"
    "relations: []\n"
    "provenance:\n"
    "  sources: []\n"
    "unit_kind: answer\n"
    "question: How is a demo routing task handled?\n"
    "reads: []\n"
    "requires: []\n"
    "---\n\n"
    "# Demo Guide\n\nFixture unit body.\n"
)

CONFIG_POLICY_FIXTURE = {
    ".hydra-framework/config/engine-policy.yaml": engine_policy_fixture(),
    ".hydra-framework/config/delegation-policy.yaml": DELEGATION_POLICY_FIXTURE,
}

PROVIDER_CAPABILITY_MAPS_FIXTURE = {
    ".hydra-framework/adapters/providers/claude/capability-map.yaml": (
        "schema: hydra-framework.capability-map.v1\n"
        "provider: claude\n"
        "verified: fixture\n"
        "certainty: fixture\n"
        "delegation_controls:\n"
        "  generated_agent_policy: supported\n"
        "  generic_subagent_start_context: advisory\n"
        "  effort_class_capping: supported\n"
        "  max_active_workers: advisory\n"
        "  max_depth: advisory\n"
    ),
    ".hydra-framework/adapters/providers/codex/capability-map.yaml": (
        "schema: hydra-framework.capability-map.v1\n"
        "provider: codex\n"
        "verified: fixture\n"
        "certainty: fixture\n"
        "delegation_controls:\n"
        "  generated_agent_policy: supported\n"
        "  generic_subagent_start_context: advisory\n"
        "  effort_class_capping: supported\n"
        "  max_active_workers: advisory\n"
        "  max_depth: advisory\n"
    ),
}

BASE_FIXTURE: dict[str, str] = {
    "AI_SYSTEM.md": "# AI System Entry Point\n\nFixture placeholder.\n",
    "AGENTS.md": "# AGENTS\n\nFixture placeholder.\n",
    ".hydra-framework/README.md": "# Hydra Framework\n\nFixture placeholder.\n",
    ".hydra-framework/manifest.yaml": (
        "schema: hydra-framework.manifest.v1\n"
        "framework_name: hydra-framework\n"
        "seed_version: 0.1.0\n"
        "status: foundation-seed\n"
        "entry_point: ../AI_SYSTEM.md\n"
    ),
    ".hydra-framework/core/placement-rules.md": "# Placement Rules\n\nFixture placeholder.\n",
    ".hydra-framework/tasks/templates/task.md": TASK_TEMPLATE,
    ".hydra-framework/tasks/templates/checkpoint.md": CHECKPOINT_TEMPLATE,
    ".hydra-framework/tasks/personal/.gitkeep": "",
    ".hydra-framework/capabilities/skills/.gitkeep": "",
    ".hydra-framework/capabilities/agents/.gitkeep": "",
    # validate_capability_maps() requires these to exist for every PROVIDERS
    # entry with an agents_target, regardless of whether any agent exists yet.
    ".hydra-framework/adapters/providers/claude/capability-map.yaml": (
        "schema: hydra-framework.capability-map.v1\n"
        "provider: claude\n"
        "verified: fixture\n"
        "certainty: fixture\n"
    ),
    ".hydra-framework/adapters/providers/codex/capability-map.yaml": (
        "schema: hydra-framework.capability-map.v1\n"
        "provider: codex\n"
        "verified: fixture\n"
        "certainty: fixture\n"
    ),
}


def hydra_object_markdown(
    *,
    hydra_id: str,
    title: str,
    kind: str = "knowledge-unit",
    status: str = "accepted",
    scope: str = "repo-local",
    uid: str = FROZEN_UID,
    schema_version: int = 3,
) -> str:
    """A minimal canonical Hydra object: full required envelope fields, so
    `validate_object_references()` finds nothing missing (see resolver.py's
    `missing_envelope_fields` / `REQUIRED_ENVELOPE_FIELDS`)."""
    return (
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {uid}\n"
        f"schema_version: {schema_version}\n"
        f"kind: {kind}\n"
        f"title: {title}\n"
        f"status: {status}\n"
        f"scope: {scope}\n"
        "owners:\n"
        "  team: fixture-owners\n"
        "relations: []\n"
        "provenance:\n"
        "  sources: []\n"
        "---\n\n"
        f"# {title}\n\nFixture object body.\n"
    )


def frozen_ports() -> ExitStack:
    """Patch every determinism port to a fixed value for the duration of a
    golden run. Callers use this as a context manager around `run_golden`."""
    stack = ExitStack()
    stack.enter_context(mock.patch("hydra_engine.ports.clock.today", return_value=FROZEN_TODAY))
    stack.enter_context(mock.patch("hydra_engine.ports.clock.now_utc_iso", return_value=FROZEN_UTC_ISO))
    stack.enter_context(mock.patch("hydra_engine.ports.clock.now_local_iso_seconds", return_value=FROZEN_LOCAL_ISO))
    stack.enter_context(mock.patch("hydra_engine.ports.clock.filename_stamp", return_value=FROZEN_STAMP))
    stack.enter_context(mock.patch("hydra_engine.ports.uids.new_uid", return_value=FROZEN_UID))
    # Deterministic regardless of the machine's real global `git config
    # user.email`: without this, owner resolution would silently pick up
    # whatever the running machine has configured. Tests that want a
    # resolved owner pass `owner=` to `run_golden`, which sets `HYDRA_OWNER`
    # and short-circuits before `resolve_owner()` ever calls this port.
    stack.enter_context(mock.patch("hydra_engine.ports.git.config_email", return_value=""))
    return stack


def run_golden(
    argv: list[str],
    *,
    extra_fixture: dict[str, str] | None = None,
    owner: str | None = None,
    stdin: str | None = None,
    pre_run=None,
) -> CommandOutcome:
    """Run one command against `BASE_FIXTURE` plus `extra_fixture`, with every
    determinism port frozen. `owner`, if given, sets `HYDRA_OWNER` for the
    duration of the call so owner-resolving commands don't fall back to the
    real machine's `git config user.email`."""
    fixture = dict(BASE_FIXTURE)
    fixture.update(extra_fixture or {})
    with frozen_ports():
        with ExitStack() as env_stack:
            if owner is not None:
                env_stack.enter_context(mock.patch.dict("os.environ", {"HYDRA_OWNER": owner}))
            if stdin is not None:
                env_stack.enter_context(mock.patch("sys.stdin", io.StringIO(stdin)))
            return run_command(argv, fixture=fixture, pre_run=pre_run)


@contextlib.contextmanager
def external_file(content: str):
    """A real, absolute-path temp file outside the sealed fixture tree.

    `--file` arguments (summarize-log, retry-guard, hook-token
    command-result) resolve against the real process cwd, not the fixture
    root — they read an arbitrary log file, not Hydra state — so a fixture
    dict can't provide one. This is the one honest way to hand such a
    command real, absolute-path content the golden can still scrub.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as handle:
        handle.write(content)
        path = handle.name
    try:
        yield path
    finally:
        Path(path).unlink(missing_ok=True)


@contextlib.contextmanager
def external_dir(fixture: dict[str, str] | None = None):
    """A real, absolute-path temp directory outside the sealed fixture tree.

    `init --target` and `diff-base --base` each name a *second* repository
    root, distinct from the one under test — `run_command`'s single sealed
    tmp tree can't express two roots, so this is the honest second one.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel_path, content in (fixture or {}).items():
            target = root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        yield root


def git_init(root: Path) -> None:
    """A `pre_run` hook: initialize a real git repo in the fixture root, for
    goldens (`install-hooks`) whose happy path needs actual git plumbing
    rather than a determinism port."""
    # Git's configured default branch is machine-dependent (`main` locally,
    # often `master` on CI), and its bundled sample hooks vary by Git version.
    # Both details are part of the fixture manifest, so pin the branch and
    # remove generated sample hooks to keep contract goldens portable.
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(root), check=True)
    hooks = root / ".git" / "hooks"
    for sample in hooks.glob("*.sample"):
        sample.unlink()


def scrub(text: str, replacements: dict[str, str]) -> str:
    for value, placeholder in replacements.items():
        if value:
            text = text.replace(value, placeholder)
    return text


def ordered_manifest(manifest: dict[str, str | None], previous: dict[str, str | None] | None = None) -> dict[str, str | None]:
    """Key order for a golden's `manifest` block, so re-recording with zero
    source changes is a no-op diff.

    The manifest is a fixture-tree file-hash listing the harness records for
    reproducibility, not command output, and it arrives in whatever order the
    tree walk produced. Sorting alone is not enough: an existing golden was
    stored in some order, and re-sorting it churns the file whenever a
    fixture gains or loses a path. So keep whatever order the stored golden
    already used for the keys it still has, and append genuinely new keys
    sorted. `assert_golden` therefore dumps without `sort_keys` -- sorting
    the payload would discard exactly this ordering. Dict equality ignores
    order, so comparison is unaffected either way; this is purely about the
    stored file staying stable.
    """
    previous = previous or {}
    ordered: dict[str, str | None] = {}
    for key in previous:
        if key in manifest:
            ordered[key] = manifest[key]
    for key in sorted(manifest):
        if key not in ordered:
            ordered[key] = manifest[key]
    return ordered


def _golden_payload(
    outcome: CommandOutcome,
    *,
    stdout_replacements: dict[str, str] | None = None,
    stderr_replacements: dict[str, str] | None = None,
    previous: dict | None = None,
) -> dict:
    previous_manifest = previous.get("manifest") if previous else None
    return {
        "exit_code": outcome.exit_code,
        "manifest": ordered_manifest(
            outcome.manifest,
            previous_manifest if isinstance(previous_manifest, dict) else None,
        ),
        "stderr": scrub(outcome.stderr, stderr_replacements or {}),
        "stdout": scrub(outcome.stdout, stdout_replacements or {}),
    }


def assert_golden(
    testcase: unittest.TestCase,
    name: str,
    outcome: CommandOutcome,
    *,
    stdout_replacements: dict[str, str] | None = None,
    stderr_replacements: dict[str, str] | None = None,
) -> None:
    """Assert `outcome` matches the stored golden for `name`, or (with
    `HYDRA_RECORD_GOLDEN=1`) write it as the new golden.

    `stdout_replacements`/`stderr_replacements` scrub run-specific absolute
    paths (e.g. a golden's own throwaway tmpdir for `init --target` or
    `diff-base --base`) to a fixed placeholder before storing or comparing,
    so the golden itself stays stable across machines and runs.
    """
    path = GOLDENS_DATA_DIR / f"{name}.json"
    previous = json.loads(path.read_text()) if path.exists() else None
    actual = _golden_payload(
        outcome,
        stdout_replacements=stdout_replacements,
        stderr_replacements=stderr_replacements,
        previous=previous if isinstance(previous, dict) else None,
    )
    if recording_enabled():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual, indent=2) + "\n")
        return
    testcase.assertTrue(path.exists(), f"no golden recorded at {path}; re-run with HYDRA_RECORD_GOLDEN=1")
    expected = previous
    testcase.assertEqual(actual, expected, f"golden mismatch for `{name}`")
