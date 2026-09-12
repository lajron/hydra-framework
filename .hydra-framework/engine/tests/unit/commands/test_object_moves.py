"""Mirror test for `hydra_engine.commands.object_moves`."""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import object_moves  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _paths() -> ObjectLocations:
    root = Path(tempfile.mkdtemp(prefix="commands-object-moves-"))
    hydra = root / ".hydra-framework"
    hydra.mkdir(parents=True)
    return ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _object_markdown(hydra_id: str, *, uid: str = "00000000-0000-0000-0000-000000000000", title: str = "Fixture") -> str:
    return (
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {uid}\n"
        "schema_version: 3\n"
        "kind: knowledge-unit\n"
        f"title: {title}\n"
        "status: active\n"
        "scope: repo\n"
        "owners:\n"
        "  team: fixture\n"
        "relations: []\n"
        "provenance:\n"
        "  sources: []\n"
        "---\n"
        f"# {title}\n"
    )


def _write(paths: ObjectLocations, rel: str, content: str) -> Path:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _move_args(source: str, destination: str, *, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(source=source, destination=destination, dry_run=dry_run)


class CommandMoveObjectTests(unittest.TestCase):
    def test_dry_run_reports_without_moving(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        destination = str(paths.hydra / "knowledge-units/0001-moved.md")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = object_moves.command_move_object(_move_args(str(source), destination, dry_run=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Would move", out.getvalue())
        self.assertTrue(source.exists())

    def test_real_move_relocates_and_reindexes(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        destination = paths.hydra / "knowledge-units/0001-moved.md"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = object_moves.command_move_object(_move_args(str(source), str(destination)), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(source.exists())
        self.assertTrue(destination.exists())
        self.assertIn("Indexed 1 objects", out.getvalue())
        self.assertTrue(paths.object_registry.exists())

    def test_registry_write_refusal_from_a_concurrency_race_still_completes_the_move(self):
        # B3: the file move already succeeded and references already
        # validated by the time the registry write races a concurrent
        # atomic replace, so refuse just that write and advise a rerun
        # rather than reverting a move that was otherwise correct.
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        destination = paths.hydra / "knowledge-units/0001-moved.md"
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(object_moves, "write_object_registry", return_value=None):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result = object_moves.command_move_object(_move_args(str(source), str(destination)), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(source.exists())
        self.assertTrue(destination.exists())
        self.assertIn("registry write refused", err.getvalue())
        self.assertFalse(paths.object_registry.exists())

    def test_destination_already_exists_refuses(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        destination = _write(paths, "knowledge-units/0001-moved.md", "already here\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = object_moves.command_move_object(_move_args(str(source), str(destination)), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("destination already exists", err.getvalue())

    def test_destination_suffix_mismatch_refuses(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        destination = str(paths.hydra / "knowledge-units/0001-moved.txt")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = object_moves.command_move_object(_move_args(str(source), destination), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("must keep the `.md` suffix", err.getvalue())
        self.assertTrue(source.exists())

    def test_broken_references_precondition_refuses(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        _write(
            paths, "knowledge-units/0002.md",
            _object_markdown("hydra://knowledge-unit/0002-fixture").replace(
                "relations: []", "relations:\n- hydra://knowledge-unit/missing"
            ),
        )
        destination = str(paths.hydra / "knowledge-units/0001-moved.md")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = object_moves.command_move_object(_move_args(str(source), destination), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra move-object: failed", err.getvalue())
        self.assertTrue(source.exists())

    def test_leaves_hydra_id_and_uid_untouched(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture", uid="11111111-1111-4111-8111-111111111111"))
        destination = str(paths.hydra / "knowledge-units/moved/0001.md")
        with contextlib.redirect_stdout(io.StringIO()):
            result = object_moves.command_move_object(_move_args(str(source), destination), paths)
        self.assertEqual(result.exit_code, 0)
        moved_text = (paths.hydra / "knowledge-units/moved/0001.md").read_text(encoding="utf-8")
        self.assertIn("hydra_id: hydra://knowledge-unit/0001-fixture", moved_text)
        self.assertIn("uid: 11111111-1111-4111-8111-111111111111", moved_text)

    def test_into_an_existing_directory_keeps_the_filename(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        (paths.hydra / "archive").mkdir(parents=True, exist_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            result = object_moves.command_move_object(_move_args(str(source), str(paths.hydra / "archive")), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.hydra / "archive/0001.md").exists())

    def test_treats_a_trailing_slash_as_a_directory(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        with contextlib.redirect_stdout(io.StringIO()):
            result = object_moves.command_move_object(_move_args(str(source), str(paths.hydra / "archive") + "/"), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.hydra / "archive/0001.md").exists())

    def test_updates_a_sidecar_path(self):
        paths = _paths()
        _write(paths, "knowledge/notes.md", "# Notes\n")
        _write(
            paths, "object-sidecars.yaml",
            "schema: hydra-framework.object-sidecar.v1\n"
            "objects:\n"
            "  notes:\n"
            "    hydra_id: hydra://knowledge-slice/notes\n"
            "    uid: 11111111-1111-4111-8111-111111111111\n"
            "    schema_version: 3\n"
            "    kind: knowledge-slice\n"
            "    title: Notes\n"
            "    status: active\n"
            "    scope: base-seed\n"
            "    owners:\n"
            "      team: hydra\n"
            "    relations: []\n"
            "    path: .hydra-framework/knowledge/notes.md\n"
            "    provenance:\n"
            "      sources: []\n",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = object_moves.command_move_object(
                _move_args(str(paths.hydra / "knowledge/notes.md"), str(paths.hydra / "knowledge/archive/notes.md")), paths,
            )
        self.assertEqual(result.exit_code, 0)
        sidecar_text = (paths.hydra / "object-sidecars.yaml").read_text(encoding="utf-8")
        self.assertIn("path: .hydra-framework/knowledge/archive/notes.md", sidecar_text)

    def test_dry_run_leaves_the_registry_unchanged(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        with contextlib.redirect_stdout(io.StringIO()):
            object_moves.command_move_object(argparse.Namespace(source=str(source), destination=str(paths.hydra / "knowledge-units/0001-moved.md"), dry_run=False), paths)
        registry_before = paths.object_registry.read_text(encoding="utf-8")
        source2 = paths.hydra / "knowledge-units/0001-moved.md"
        with contextlib.redirect_stdout(io.StringIO()):
            result = object_moves.command_move_object(_move_args(str(source2), str(paths.hydra / "knowledge-units/0001-again.md"), dry_run=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertFalse((paths.hydra / "knowledge-units/0001-again.md").exists())
        self.assertEqual(paths.object_registry.read_text(encoding="utf-8"), registry_before)

    def test_reverts_a_move_that_would_break_references(self):
        # cognition/ is derived state and is excluded from YAML object
        # discovery, so moving an object there unregisters it.
        paths = _paths()
        source = _write(
            paths, "tools.yaml",
            "hydra_id: hydra://capability/tools\n"
            "uid: 11111111-1111-4111-8111-111111111111\n"
            "schema_version: 3\n"
            "kind: capability\n"
            "title: Tools\n"
            "status: active\n"
            "scope: base-seed\n"
            "owners:\n"
            "  team: hydra\n"
            "relations: []\n"
            "provenance:\n"
            "  sources: []\n",
        )
        _write(paths, "knowledge/pointer.md", "Owned by hydra://capability/tools.\n")
        before = source.read_text(encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            result = object_moves.command_move_object(_move_args(str(source), str(paths.hydra / "cognition/tools.yaml")), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("would break references; reverted", err.getvalue())
        self.assertTrue(source.exists())
        self.assertEqual(source.read_text(encoding="utf-8"), before)
        self.assertFalse((paths.hydra / "cognition/tools.yaml").exists())

    def test_refuses_a_non_object_source(self):
        paths = _paths()
        _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        plain = _write(paths, "notes/plain.md", "# Plain\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = object_moves.command_move_object(_move_args(str(plain), str(paths.hydra / "notes/moved.md")), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("is not a canonical Hydra object", err.getvalue())

    def test_refuses_a_tier_change(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = object_moves.command_move_object(_move_args(str(source), str(paths.local / "knowledge-units/0001.md")), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("changes state tier", err.getvalue())

    def test_requires_a_uid(self):
        paths = _paths()
        source = _write(
            paths, "knowledge-units/0001.md",
            "---\nhydra_id: hydra://knowledge-unit/0001-fixture\nkind: knowledge-unit\ntitle: Fixture\nstatus: active\n"
            "scope: repo\nrelations:\nprovenance:\n  sources: []\n---\n# Fixture\n",
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = object_moves.command_move_object(_move_args(str(source), str(paths.hydra / "knowledge-units/moved.md")), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("has no uid", err.getvalue())

    def test_reports_files_that_still_cite_the_old_path(self):
        paths = _paths()
        source = _write(paths, "knowledge-units/0001.md", _object_markdown("hydra://knowledge-unit/0001-fixture"))
        _write(paths, "knowledge/pointer.md", "See `.hydra-framework/knowledge-units/0001.md`.\n")
        destination = str(paths.hydra / "knowledge-units/moved/0001.md")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = object_moves.command_move_object(_move_args(str(source), destination), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("note: .hydra-framework/knowledge/pointer.md still cites", out.getvalue())


def _skill_metadata(name: str, uid: str = "00000000-0000-0000-0000-0000000000ab") -> str:
    return (
        "schema: hydra-framework.skill.v2\n"
        f"hydra_id: hydra://capability/skill/{name}\n"
        f"uid: {uid}\n"
        "schema_version: 3\n"
        "hydra_object_kind: skill\n"
        f"name: {name}\n"
        "description: Use when relevant.\n"
        "status: active\n"
        "scope: repo-local\n"
        "owners:\n"
        "  team: fixture\n"
        "relations: []\n"
        "provenance:\n"
        "  sources: []\n"
    )


class CanonicalRenameStaleNoticeTests(unittest.TestCase):
    """`move-object` on a canonical skill/agent rename must print the same
    removal line `providers.reclaim`'s stale-wrapper report would."""

    def _generated_wrapper(self, paths: ObjectLocations, slug: str) -> None:
        wrapper = paths.root / f".claude/skills/hydra-{slug}/SKILL.md"
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text("generated body\n", encoding="utf-8")
        (wrapper.parent / ".hydra-adapter.yaml").write_text(
            "schema: hydra-framework.adapter.v2\nprovider: claude\nkind: skill\n"
            f"canonical_source: .hydra-framework/capabilities/skills/{slug}/skill.md\ngenerated_file: SKILL.md\n",
            encoding="utf-8",
        )

    def test_rename_prints_the_removal_line_for_the_old_wrapper(self):
        paths = _paths()
        source = _write(paths, "capabilities/skills/foo/metadata.yaml", _skill_metadata("foo"))
        _write(paths, "capabilities/skills/foo/skill.md", "# Foo\n")
        self._generated_wrapper(paths, "foo")
        destination = paths.hydra / "capabilities/skills/bar/metadata.yaml"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = object_moves.command_move_object(_move_args(str(source), str(destination)), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("stale: .claude/skills/hydra-foo/SKILL.md", out.getvalue())
        self.assertIn("rm -rf .claude/skills/hydra-foo/", out.getvalue())

    def test_no_notice_when_no_wrapper_was_ever_generated(self):
        paths = _paths()
        source = _write(paths, "capabilities/skills/foo/metadata.yaml", _skill_metadata("foo"))
        _write(paths, "capabilities/skills/foo/skill.md", "# Foo\n")
        destination = paths.hydra / "capabilities/skills/bar/metadata.yaml"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = object_moves.command_move_object(_move_args(str(source), str(destination)), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("stale:", out.getvalue())

    def test_no_notice_when_the_slug_is_unchanged(self):
        paths = _paths()
        source = _write(paths, "capabilities/skills/foo/metadata.yaml", _skill_metadata("foo"))
        _write(paths, "capabilities/skills/foo/skill.md", "# Foo\n")
        self._generated_wrapper(paths, "foo")
        destination = paths.hydra / "capabilities/skills/foo/metadata-renamed.yaml"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = object_moves.command_move_object(_move_args(str(source), str(destination)), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("stale:", out.getvalue())


if __name__ == "__main__":
    unittest.main()
