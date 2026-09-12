"""Git tracking for generated provider adapters: the narrow ignore patterns
derived from `PROVIDERS`/`WRAPPER_PREFIX`, and the ownership-vs-Git checks
that keep the ignore rules honest.

Two one-directional statements are the whole invariant (an ignore glob and a
finite ownership index cannot be asserted equal, only checked each direction):
every `ownership_paths()` member is ignored, and every path Git actually
ignores beneath a provider target is a verified `ownership_paths()` member.
"""

from __future__ import annotations

from pathlib import Path

from hydra_engine.documents.tokens import display_path, read_text, write_text
from hydra_engine.finding import Finding
from hydra_engine.ports import git as git_port
from hydra_engine.providers.adapter_plan import ownership_paths
from hydra_engine.providers.capabilities import PROVIDERS, WRAPPER_PREFIX
from hydra_engine.providers.paths import ProvidersPaths

IGNORE_BLOCK_HEADER = "# BEGIN hydra generated adapters (managed by hydra.py export-adapters)"
IGNORE_BLOCK_FOOTER = "# END hydra generated adapters"


def generated_adapter_ignore_patterns() -> tuple[str, ...]:
    """Ignore patterns for every Hydra-generated adapter path, derived from
    `PROVIDERS` and `WRAPPER_PREFIX` rather than hand-written, so a provider
    added later, or a changed prefix, is covered with no second edit. Ignores
    only the generated wrapper units themselves, never a whole provider
    directory: a hand-authored `.claude/skills/deploy/` stays trackable."""
    patterns: list[str] = []
    for provider in PROVIDERS:
        patterns.append(f"{provider.skills_target}/{WRAPPER_PREFIX}*/")
        if provider.agents_target is None or provider.agent_extension is None:
            continue
        patterns.append(f"{provider.agents_target}/{WRAPPER_PREFIX}*{provider.agent_extension}")
        patterns.append(f"{provider.agents_target}/.hydra-adapter-{WRAPPER_PREFIX}*.yaml")
    return tuple(patterns)


def render_generated_adapter_ignore_block() -> str:
    lines = [IGNORE_BLOCK_HEADER, *generated_adapter_ignore_patterns(), IGNORE_BLOCK_FOOTER]
    return "\n".join(lines) + "\n"


def ensure_generated_adapter_ignore_block(root: Path) -> str:
    """Add or refresh the marked ignore block in `.gitignore`. Idempotent:
    a second call with the same `PROVIDERS`/`WRAPPER_PREFIX` is a no-op; a
    changed registry rewrites the block in place rather than appending a
    second one."""
    gitignore = root / ".gitignore"
    text = read_text(gitignore) if gitignore.exists() else ""
    block = render_generated_adapter_ignore_block()
    lines = text.splitlines()
    if IGNORE_BLOCK_HEADER in lines:
        start = lines.index(IGNORE_BLOCK_HEADER)
        try:
            end = lines.index(IGNORE_BLOCK_FOOTER, start) + 1
        except ValueError:
            end = start + 1
        existing_block = "\n".join(lines[start:end])
        if existing_block == block.rstrip("\n"):
            return "already-present"
        lines[start:end] = block.rstrip("\n").splitlines()
        write_text(gitignore, "\n".join(lines) + "\n")
        return "updated"

    prefix = "" if not text else "\n" if text.endswith("\n") else "\n\n"
    write_text(gitignore, f"{text}{prefix}{block}")
    return "added"


def _provider_targets(paths: ProvidersPaths) -> tuple[str, ...]:
    targets: list[str] = []
    for provider in PROVIDERS:
        targets.append(provider.skills_target)
        if provider.agents_target is not None:
            targets.append(provider.agents_target)
    return tuple(dict.fromkeys(targets))


def unignored_ownership_findings(paths: ProvidersPaths) -> list[Finding]:
    """Every `ownership_paths()` member must be ignored by Git, whether or
    not it currently exists on disk -- `git check-ignore` matches by pattern
    against a path, not by what is materialized."""
    findings: list[Finding] = []
    for owned in sorted(ownership_paths(paths)):
        rel = display_path(owned, paths.root)
        if not git_port.ignore_match(paths.root, rel):
            findings.append(Finding(
                path=rel, code="git-ownership",
                detail=f"{rel} is a Hydra-owned adapter path but Git does not ignore it; "
                "the generated-adapter ignore block is missing or does not cover it",
            ))
    return findings


def tracked_ownership_findings(paths: ProvidersPaths) -> list[Finding]:
    """No path Hydra owns may remain tracked once generated adapters are
    untracked: `git rm -r --cached` must have removed every one of them."""
    findings: list[Finding] = []
    for owned in sorted(ownership_paths(paths)):
        rel = display_path(owned, paths.root)
        if git_port.is_tracked(paths.root, rel):
            findings.append(Finding(
                path=rel, code="git-ownership",
                detail=f"{rel} is a Hydra-owned adapter path and must not remain tracked after migration",
            ))
    return findings


def unverified_ignored_provider_findings(paths: ProvidersPaths) -> list[Finding]:
    """Every path Git actually ignores beneath a provider target must be a
    verified `ownership_paths()` member. This is what catches a hand-authored
    `.claude/skills/hydra-deploy/` the ignore glob also swallows: it is
    ignored and under a provider target, but Hydra never generated it."""
    findings: list[Finding] = []
    owned = ownership_paths(paths)
    owned_rel = {display_path(path, paths.root) for path in owned}
    for target in _provider_targets(paths):
        for rel in git_port.ignored_files(paths.root, target):
            if rel not in owned_rel:
                findings.append(Finding(
                    path=rel, code="git-ownership",
                    detail=f"{rel} is ignored by Git under a provider target but is not a verified "
                    "Hydra adapter path; a hand-authored file may be silently unrecoverable on a fresh clone",
                ))
    return findings


def tracked_and_ignored_provider_findings(paths: ProvidersPaths) -> list[Finding]:
    """No tracked provider file (a stable integration file such as
    `settings.json` or `hydra-placement.md`) may also match an ignore
    pattern: that would make it invisible to a future `git add` after a
    working-tree loss."""
    findings: list[Finding] = []
    for target in _provider_targets(paths):
        for rel in git_port.tracked_files(paths.root, target):
            match = git_port.ignore_match(paths.root, rel, no_index=True)
            if match:
                findings.append(Finding(
                    path=rel, code="git-ownership",
                    detail=f"{rel} is tracked but also matches a Git ignore rule ({match}); "
                    "a tracked provider file must never be ignored",
                ))
    return findings
