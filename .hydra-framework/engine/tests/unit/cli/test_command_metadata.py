"""Unit tests for hydra_engine.cli.command_metadata."""

from __future__ import annotations

import argparse
import json
import unittest

from hydra_engine.cli import command_metadata
from hydra_engine.cli import dispatch
from hydra_engine.cli import parser as cli_parser


class _Leaf:
    @staticmethod
    def register(subparsers):
        plain = subparsers.add_parser("plain")
        plain.set_defaults(func=lambda args, ctx: 0)

        group = subparsers.add_parser("group")
        group_sub = group.add_subparsers(dest="group_command", required=True)
        child = group_sub.add_parser("child", aliases=["kid"])
        child.add_argument("name")
        child.add_argument("--force", action="store_true")
        child.set_defaults(func=lambda args, ctx: 0)


class GenerateCommandMetadataTests(unittest.TestCase):
    def _parser(self) -> argparse.ArgumentParser:
        return cli_parser.build_parser((_Leaf,))

    def test_walks_leaf_and_grouped_commands(self) -> None:
        entries = command_metadata.generate_command_metadata(self._parser())
        ids = [entry.id for entry in entries]
        self.assertEqual(ids, ["group child", "plain"])

    def test_own_arguments_exclude_help_and_capture_positionals_and_flags(self) -> None:
        entries = command_metadata.generate_command_metadata(self._parser())
        child = next(entry for entry in entries if entry.id == "group child")
        self.assertEqual(child.arguments, ("name", "--force"))

    def test_argparse_aliases_are_recovered_from_the_shared_parser_instance(self) -> None:
        entries = command_metadata.generate_command_metadata(self._parser())
        child = next(entry for entry in entries if entry.id == "group child")
        self.assertEqual(child.aliases, ("kid",))

    def test_commands_with_no_overlay_entry_have_no_safety(self) -> None:
        entries = command_metadata.generate_command_metadata(self._parser())
        plain = next(entry for entry in entries if entry.id == "plain")
        self.assertIsNone(plain.safety)

    def test_known_conditional_and_fingerprint_writes_have_safety_metadata(self) -> None:
        self.assertIn("bindings verify", command_metadata.SIDE_EFFECT_COMMANDS)
        self.assertIn("knowledge fingerprint", command_metadata.SIDE_EFFECT_COMMANDS)
        self.assertIn("wiki fingerprint", command_metadata.SIDE_EFFECT_COMMANDS)


class RenderTests(unittest.TestCase):
    def test_json_round_trips_id_arguments_and_safety_fields(self) -> None:
        entries = [
            command_metadata.CommandMetadata(
                id="task complete", aliases=(), arguments=("task", "--force"),
                safety=command_metadata.SIDE_EFFECT_COMMANDS["task complete"],
            ),
            command_metadata.CommandMetadata(id="board", aliases=(), arguments=("--owner", "--json"), safety=None),
        ]
        data = json.loads(command_metadata.render(entries, as_json=True))
        by_id = {row["id"]: row for row in data}
        self.assertEqual(by_id["task complete"]["arguments"], ["task", "--force"])
        self.assertIn("side_effects", by_id["task complete"])
        self.assertNotIn("side_effects", by_id["board"])

    def test_text_rendering_omits_safety_lines_for_read_only_commands(self) -> None:
        entries = [command_metadata.CommandMetadata(id="board", aliases=(), arguments=(), safety=None)]
        text = command_metadata.render(entries, as_json=False)
        self.assertIn("board -- arguments: (none)", text)
        self.assertNotIn("side_effects", text)


class SideEffectOverlayMatchesLiveCommandsTests(unittest.TestCase):
    """Guards every hand-authored overlay key against the live command tree."""

    def test_every_overlay_key_is_a_real_registered_command(self) -> None:
        parser = cli_parser.build_parser(dispatch.COMMAND_MODULES, dispatch._register_direct_commands)
        live_ids = {entry.id for entry in command_metadata.generate_command_metadata(parser)}
        stale = set(command_metadata.SIDE_EFFECT_COMMANDS) - live_ids
        self.assertEqual(stale, set())

    def test_known_mutating_commands_are_not_left_without_overlay_metadata(self) -> None:
        parser = cli_parser.build_parser(dispatch.COMMAND_MODULES, dispatch._register_direct_commands)
        live = {entry.id: entry for entry in command_metadata.generate_command_metadata(parser)}
        for command_id in ("bindings verify", "knowledge fingerprint", "wiki fingerprint"):
            self.assertIsNotNone(live[command_id].safety)

    def test_orchestration_mutations_have_safety_metadata_and_status_is_read_only(self) -> None:
        parser = cli_parser.build_parser(dispatch.COMMAND_MODULES, dispatch._register_direct_commands)
        live = {entry.id: entry for entry in command_metadata.generate_command_metadata(parser)}
        for command_id in (
            "orchestration start", "orchestration spawn", "orchestration message",
            "orchestration collect", "orchestration transition", "orchestration handoff",
            "orchestration recover", "orchestration review", "orchestration validate",
        ):
            self.assertIsNotNone(live[command_id].safety)
        self.assertIsNone(live["orchestration status"].safety)


if __name__ == "__main__":
    unittest.main()
