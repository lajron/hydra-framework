"""Mirror tests for `hydra_engine.wiki.sidecar_entries`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.wiki.sidecar_entries import read_sidecar_entries  # noqa: E402


def _sidecar(objects: str) -> str:
    return (
        "schema: hydra-framework.object-sidecar.v1\n"
        "title: Fixture Wiki\n"
        "objects:\n"
        f"{objects}"
    )


class SidecarEntriesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.sidecar = self.root / ".hydra-framework/surfaces/wiki/fixture.yaml"
        self.sidecar.parent.mkdir(parents=True)

    def write(self, content: str) -> None:
        self.sidecar.write_text(content, encoding="utf-8")

    def test_reads_provenance_fields_and_allows_unknown_fields(self) -> None:
        self.write(_sidecar(
            "  page:\n"
            "    hydra_id: hydra://documentation/page/fixture\n"
            "    path: project-wiki/fixture.md\n"
            "    checked_on: '2026-01-01'\n"
            "    custom: value\n"
            "    custom_block:\n"
            "      nested: value\n"
            "    provenance:\n"
            "      sources:\n"
            "        - source.py\n"
            "      source_digests:\n"
            "        - source: source.py\n"
            "          digest: sha256:0000000000000000000000000000000000000000000000000000000000000000\n"
        ))
        entries = read_sidecar_entries(self.sidecar, self.root)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "page")
        self.assertEqual(entries[0].hydra_id, "hydra://documentation/page/fixture")
        self.assertEqual(entries[0].sources, ["source.py"])
        self.assertEqual(entries[0].source_digests[0]["source"], "source.py")

    def test_missing_checked_on_is_read_as_unset(self) -> None:
        self.write(_sidecar(
            "  page:\n"
            "    hydra_id: hydra://documentation/page/fixture\n"
            "    path: project-wiki/fixture.md\n"
            "    provenance:\n"
            "      sources: []\n"
        ))
        self.assertEqual(read_sidecar_entries(self.sidecar, self.root)[0].checked_on, "")

    def test_rejects_duplicate_names_ids_and_consumed_keys(self) -> None:
        duplicate_name = _sidecar(
            "  page:\n"
            "    hydra_id: hydra://documentation/page/one\n"
            "    path: one.md\n"
            "    provenance:\n"
            "      sources: []\n"
            "  page:\n"
            "    hydra_id: hydra://documentation/page/two\n"
            "    path: two.md\n"
            "    provenance:\n"
            "      sources: []\n"
        )
        self.write(duplicate_name)
        with self.assertRaises(ValueError):
            read_sidecar_entries(self.sidecar, self.root)

        duplicate_id = duplicate_name.replace("  page:\n", "  first:\n", 1).replace("  page:\n", "  second:\n", 1)
        duplicate_id = duplicate_id.replace("hydra://documentation/page/two", "hydra://documentation/page/one")
        self.write(duplicate_id)
        with self.assertRaises(ValueError):
            read_sidecar_entries(self.sidecar, self.root)

        duplicate_key = _sidecar(
            "  page:\n"
            "    hydra_id: hydra://documentation/page/fixture\n"
            "    hydra_id: hydra://documentation/page/other\n"
            "    path: page.md\n"
            "    provenance:\n"
            "      sources: []\n"
        )
        self.write(duplicate_key)
        with self.assertRaises(ValueError):
            read_sidecar_entries(self.sidecar, self.root)

    def test_rejects_tabs_non_lists_and_malformed_digests(self) -> None:
        self.write(_sidecar(
            "  page:\n"
            "\thydra_id: hydra://documentation/page/fixture\n"
        ))
        with self.assertRaises(ValueError):
            read_sidecar_entries(self.sidecar, self.root)

        self.write(_sidecar(
            "  page:\n"
            "    hydra_id: hydra://documentation/page/fixture\n"
            "    path: page.md\n"
            "    provenance:\n"
            "      sources: source.py\n"
        ))
        with self.assertRaises(ValueError):
            read_sidecar_entries(self.sidecar, self.root)

        self.write(_sidecar(
            "  page:\n"
            "    hydra_id: hydra://documentation/page/fixture\n"
            "    path: page.md\n"
            "    provenance:\n"
            "      sources:\n"
            "        - source.py\n"
            "      source_digests:\n"
            "        - source: source.py\n"
            "          digest: wrong\n"
        ))
        with self.assertRaises(ValueError):
            read_sidecar_entries(self.sidecar, self.root)


if __name__ == "__main__":
    unittest.main()
