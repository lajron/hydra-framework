"""Mirror test for `hydra_engine.documents.yaml_documents`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents import yaml_documents  # noqa: E402


class ParseYamlTests(unittest.TestCase):
    def write(self, name: str, content: str) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="yaml-documents-test-"))
        path = directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_flat_scalars_and_nesting(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("nested.yaml", "name: agent\ndeps:\n  - one.md\n  - two.md\n")
        data = yaml_documents.parse_yaml(path, root)
        self.assertEqual(data["name"], "agent")
        self.assertEqual(data["deps"], ["one.md", "two.md"])

    def test_list_of_single_key_maps_round_trips(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("expand.yaml", 'items:\n  - when: "a"\n  - when: "b"\n')
        data = yaml_documents.parse_yaml(path, root)
        self.assertEqual(data["items"], [{"when": "a"}, {"when": "b"}])

    def test_list_of_multi_key_maps_with_a_nested_block_list(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        content = (
            "items:\n"
            "  - when_paths:\n"
            "      - a\n"
            "      - b\n"
            "    read:\n"
            "      - c\n"
            "    why: something\n"
        )
        path = self.write("expand.yaml", content)
        data = yaml_documents.parse_yaml(path, root)
        self.assertEqual(data["items"], [{"when_paths": ["a", "b"], "read": ["c"], "why": "something"}])

    def test_a_bare_hydra_ref_list_item_is_still_a_scalar(self):
        # `hydra://x` must not be mistaken for a `key: value` mapping item --
        # the character right after `:` is `/`, not whitespace/end.
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("refs.yaml", "items:\n  - hydra://knowledge-unit/demo/one\n")
        data = yaml_documents.parse_yaml(path, root)
        self.assertEqual(data["items"], ["hydra://knowledge-unit/demo/one"])

    def test_missing_file_returns_empty_unless_required(self):
        root = Path("/repo")
        self.assertEqual(yaml_documents.parse_yaml(Path("/nonexistent/hydra.yaml"), root), {})
        with self.assertRaises(yaml_documents.HydraYamlError):
            yaml_documents.parse_yaml(Path("/nonexistent/hydra.yaml"), root, required=True)

    def test_rejects_anchors_and_block_scalars(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        for content in ["base: &anchor\n", "ref: *anchor\n", "body: |\n  text\n", "body: >\n  text\n"]:
            path = self.write("bad.yaml", content)
            with self.assertRaises(yaml_documents.HydraYamlError):
                yaml_documents.parse_yaml(path, root)

    def test_dedents_back_to_outer_map(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("dedent.yaml", "outer:\n  inner:\n    - x\n  sibling: y\nlast: z\n")
        data = yaml_documents.parse_yaml(path, root)
        self.assertEqual(data["outer"]["inner"], ["x"])
        self.assertEqual(data["outer"]["sibling"], "y")
        self.assertEqual(data["last"], "z")

    def test_quotes_are_stripped(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("quoted.yaml", 'hint: "[start|stop] [name]"\n')
        self.assertEqual(yaml_documents.parse_yaml(path, root)["hint"], "[start|stop] [name]")

    def test_empty_flow_collections_are_preserved(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("empty.yaml", "items: []\noptions: {}\nnested:\n  - []\n  - {}\n")
        self.assertEqual(
            yaml_documents.parse_yaml(path, root),
            {"items": [], "options": {}, "nested": [[], {}]},
        )

    def test_rejects_non_empty_flow_collections(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        for content in ["items: [one, two]\n", "options: {one: two}\n", "items:\n  - [one, two]\n"]:
            path = self.write("flow.yaml", content)
            with self.assertRaisesRegex(yaml_documents.HydraYamlError, "non-empty YAML flow collections"):
                yaml_documents.parse_yaml(path, root)

    def test_quoted_flow_collection_text_remains_a_scalar(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("quoted-flow.yaml", 'list_text: "[one, two]"\nmap_text: "{one: two}"\n')
        self.assertEqual(
            yaml_documents.parse_yaml(path, root),
            {"list_text": "[one, two]", "map_text": "{one: two}"},
        )

    def test_glob_values_are_not_mistaken_for_aliases(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("glob.yaml", "allowed_tools: Bash(hydra.py task *)\npattern: '*.ts'\n")
        data = yaml_documents.parse_yaml(path, root)
        self.assertEqual(data["allowed_tools"], "Bash(hydra.py task *)")
        self.assertEqual(data["pattern"], "*.ts")

    def test_rejects_tabs_and_unterminated_quotes(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        for content in ["key:\n\t- item\n", 'key: "unterminated\n']:
            path = self.write("bad.yaml", content)
            with self.assertRaises(yaml_documents.HydraYamlError):
                yaml_documents.parse_yaml(path, root)

    def test_rejects_garbage_lines(self):
        root = Path(tempfile.mkdtemp(prefix="yaml-documents-root-"))
        path = self.write("bad.yaml", "not a mapping at all\n")
        with self.assertRaises(yaml_documents.HydraYamlError):
            yaml_documents.parse_yaml(path, root)


class YamlCoercionTests(unittest.TestCase):
    def test_yaml_list_handles_lists_and_comma_strings(self):
        self.assertEqual(yaml_documents.yaml_list(["a", "b"]), ["a", "b"])
        self.assertEqual(yaml_documents.yaml_list("a, b ,c"), ["a", "b", "c"])
        self.assertEqual(yaml_documents.yaml_list(None), [])

    def test_yaml_map_str_int_fall_back(self):
        self.assertEqual(yaml_documents.yaml_map("nope"), {})
        self.assertEqual(yaml_documents.yaml_str(None, "fallback"), "fallback")
        self.assertEqual(yaml_documents.yaml_int("3", 0), 3)
        self.assertEqual(yaml_documents.yaml_int("nope", 7), 7)

    def test_yaml_quote_round_trips_through_json(self):
        self.assertEqual(yaml_documents.yaml_quote('a "quoted" value'), '"a \\"quoted\\" value"')


if __name__ == "__main__":
    unittest.main()
