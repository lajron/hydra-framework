from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from hydra_engine.commands.knowledge_bindings import command_bindings_list, command_bindings_verify
from hydra_engine.knowledge.packages import ContextCompilerPaths


class _Args:
    def __init__(self, name: str | None = None, accept: bool = False):
        self.name = name
        self.accept = accept


def _repo(root: Path, *, extra_binding: str = "") -> ContextCompilerPaths:
    bindings = root / ".hydra-framework/repo/knowledge/bindings"
    bindings.mkdir(parents=True)
    (root / "src/app").mkdir(parents=True)
    (root / "src/app/pom.xml").write_text("<project/>\n", encoding="utf-8")
    (bindings / "manifest.yaml").write_text(
        'schema: "hydra-framework.bindings-manifest.v1"\nfragments:\n  - product.yaml\n', encoding="utf-8"
    )
    (bindings / "product.yaml").write_text(
        'schema: "hydra-framework.bindings.v1"\n'
        "namespace: product\n"
        "bindings:\n"
        "  checkout:\n"
        "    target: src/app\n"
        "    kind: directory\n"
        "    assertions:\n"
        "      contains:\n"
        "        - pom.xml\n" + extra_binding,
        encoding="utf-8",
    )
    return ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


def _run(command, args, paths) -> tuple[int, str]:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        result = command(args, paths)
    return result.exit_code, stream.getvalue()


class BindingCommandTests(unittest.TestCase):
    def test_no_manifest_is_not_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
            for command in (command_bindings_list, command_bindings_verify):
                code, out = _run(command, _Args(), paths)
                self.assertEqual(code, 0)
                self.assertIn("no bindings manifest", out)

    def test_list_reports_each_binding_and_its_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _repo(Path(tmp))
            code, out = _run(command_bindings_list, _Args(), paths)
            self.assertEqual(code, 0)
            self.assertIn("@product/checkout [stale] directory -> src/app", out)

    def test_verify_fails_until_the_fingerprint_is_reviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _repo(Path(tmp))
            code, out = _run(command_bindings_verify, _Args(), paths)
            self.assertEqual(code, 1)
            self.assertIn("fingerprint is unreviewed", out)

    def test_accept_records_the_fingerprint_and_then_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _repo(root)
            fragment = root / ".hydra-framework/repo/knowledge/bindings/product.yaml"
            before = fragment.read_text(encoding="utf-8")
            code, out = _run(command_bindings_verify, _Args(accept=True), paths)
            self.assertEqual(code, 0)
            self.assertIn("[accepted]", out)
            after = fragment.read_text(encoding="utf-8")
            self.assertIn("accepted_fingerprint:", after)
            # The rest of a hand-authored fragment is untouched.
            self.assertEqual(
                [line for line in before.splitlines() if "accepted_fingerprint" not in line],
                [line for line in after.splitlines() if "accepted_fingerprint" not in line],
            )
            code, out = _run(command_bindings_verify, _Args(), paths)
            self.assertEqual(code, 0)
            self.assertIn("[verified]", out)

    def test_accept_refuses_to_launder_a_failed_assertion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _repo(root, extra_binding="  missing:\n    target: src/nope\n    kind: directory\n    assertions: {}\n")
            code, out = _run(command_bindings_verify, _Args(accept=True), paths)
            self.assertEqual(code, 1)
            self.assertIn("@product/missing [unresolved]", out)
            self.assertIn("target does not exist", out)
            fragment = (root / ".hydra-framework/repo/knowledge/bindings/product.yaml").read_text(encoding="utf-8")
            self.assertEqual(fragment.count("accepted_fingerprint:"), 1)

    def test_accept_rewrites_rather_than_duplicates_a_stale_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _repo(root)
            fragment = root / ".hydra-framework/repo/knowledge/bindings/product.yaml"
            fragment.write_text(
                fragment.read_text(encoding="utf-8").replace(
                    "  checkout:\n", '  checkout:\n    accepted_fingerprint: "sha256:outdated"\n'
                ),
                encoding="utf-8",
            )
            _run(command_bindings_verify, _Args(accept=True), paths)
            text = fragment.read_text(encoding="utf-8")
            self.assertEqual(text.count("accepted_fingerprint:"), 1)
            self.assertNotIn("sha256:outdated", text)

    def test_selector_narrows_to_one_binding_and_rejects_an_unknown_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _repo(Path(tmp), extra_binding="  other:\n    target: src/app\n    kind: directory\n    assertions: {}\n")
            code, out = _run(command_bindings_list, _Args(name="@product/checkout"), paths)
            self.assertEqual(code, 0)
            self.assertIn("@product/checkout", out)
            self.assertNotIn("@product/other", out)
            code, _out = _run(command_bindings_list, _Args(name="@product/nope"), paths)
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
