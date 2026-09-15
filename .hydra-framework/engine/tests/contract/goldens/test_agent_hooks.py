"""agent_hooks goldens: summarize-log, retry-guard, hook-token
(both modes), hook-post-edit.

`--store-full`/log-storing flag variants remain deferred (no behavior change
to that code). The provider-surface and tier-placement notice
branches below are covered; the
package-gate branch is still deferred — it needs a canonical knowledge
package fixture that is not otherwise exercised here.
"""

from __future__ import annotations

import unittest

from .fixtures import assert_golden, external_file, hydra_object_markdown, run_golden

LOG_TEXT = "hello\nworld\n"


class AgentHooksGoldenTests(unittest.TestCase):
    def test_summarize_log_happy_path(self):
        with external_file(LOG_TEXT) as log_path:
            outcome = run_golden(["summarize-log", "--file", log_path])
            assert_golden(self, "agent-hooks-summarize-log", outcome, stdout_replacements={log_path: "<LOG_FILE>"})

    def test_retry_guard_happy_path(self):
        with external_file("boom\n") as log_path:
            outcome = run_golden(
                ["retry-guard", "--file", log_path, "--command", "x", "--exit-code", "1", "--key", "k"]
            )
            assert_golden(self, "agent-hooks-retry-guard", outcome, stdout_replacements={log_path: "<LOG_FILE>"})

    def test_hook_token_pre_context_happy_path(self):
        outcome = run_golden(["hook-token", "pre-context", "--budget", "1000", "--report"])
        assert_golden(self, "agent-hooks-hook-token-pre-context", outcome)

    def test_hook_token_command_result_happy_path(self):
        with external_file(LOG_TEXT) as log_path:
            outcome = run_golden(
                ["hook-token", "command-result", "--file", log_path, "--command", "x", "--exit-code", "1"]
            )
            assert_golden(
                self, "agent-hooks-hook-token-command-result", outcome, stdout_replacements={log_path: "<LOG_FILE>"}
            )

    def test_hook_post_edit_happy_path(self):
        """Empty stdin: the hook's own no-op path."""
        outcome = run_golden(["hook-post-edit"], stdin="")
        assert_golden(self, "agent-hooks-hook-post-edit", outcome)

    def test_hook_post_edit_registered_object_path(self):
        """A registered object path refreshes the derived registry silently."""
        path = ".hydra-framework/README.md"
        registry = (
            "schema: hydra-framework.object-registry.v1\n"
            "objects:\n"
            "  hydra://knowledge-unit/fixture-readme:\n"
            f"    path: {path}\n"
        )
        outcome = run_golden(
            ["hook-post-edit"],
            extra_fixture={
                path: hydra_object_markdown(
                    hydra_id="hydra://knowledge-unit/fixture-readme",
                    title="Fixture Readme",
                ),
                ".hydra-framework/cognition/graph/registry.yaml": registry,
            },
            stdin='{"tool_input": {"file_path": ".hydra-framework/README.md"}}',
        )
        assert_golden(self, "agent-hooks-hook-post-edit-registered", outcome)

    def test_hook_post_edit_provider_surface_orphaned(self):
        """A hand-authored `.claude/skills/...` file with no canonical Hydra
        source: the provider-surface notice's `orphaned` branch."""
        stdin = '{"tool_input": {"file_path": ".claude/skills/my-skill/SKILL.md"}}'
        outcome = run_golden(
            ["hook-post-edit"],
            extra_fixture={".claude/skills/my-skill/SKILL.md": "# My Skill\n"},
            stdin=stdin,
        )
        assert_golden(self, "agent-hooks-hook-post-edit-provider-surface-orphaned", outcome)

    def test_hook_post_edit_tier_placement_retired_task_dir(self):
        """A write into a retired task directory: the
        tier-placement notice's retired-task-directory branch."""
        stdin = '{"tool_input": {"file_path": ".hydra-framework/tasks/active/foo.md"}}'
        outcome = run_golden(
            ["hook-post-edit"],
            extra_fixture={".hydra-framework/tasks/active/foo.md": "# Foo\n"},
            stdin=stdin,
        )
        assert_golden(self, "agent-hooks-hook-post-edit-tier-placement-retired", outcome)


if __name__ == "__main__":
    unittest.main()
