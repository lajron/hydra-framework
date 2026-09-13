"""Mirror tests for `hydra_engine.knowledge.lexical_index`."""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity.slugs import slugify  # noqa: E402
from hydra_engine.knowledge import index_collection, lexical_index  # noqa: E402


def _doc(key, hydra_id="", aliases=(), path="", kind="file", package="", title="", keywords=(), routes=(), body="", relations=()):
    return index_collection.SearchDocument(
        key, hydra_id, aliases, path, kind, package, title, keywords, routes, (), (), body, relations,
    )


def _normal_path(value: str) -> str:
    return value.strip().lstrip("./")


class LexicalIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.execute(
            "CREATE TABLE documents (key TEXT PRIMARY KEY, hydra_id TEXT, aliases TEXT, path TEXT, kind TEXT, "
            "package TEXT, title TEXT, keywords TEXT, routes TEXT, use_when TEXT, headings TEXT, body TEXT, relations TEXT, content_id TEXT)"
        )

    def _insert_document_row(self, doc) -> None:
        self.conn.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', ?, ?, '')",
            (doc.key, doc.hydra_id, "\n".join(doc.aliases), doc.path, doc.kind, doc.package, doc.title,
             "\n".join(doc.keywords), "\n".join(doc.routes), doc.body, "\n".join(doc.relations)),
        )

    def test_mode_label_reflects_trigram_support(self):
        self.assertEqual(lexical_index.mode_label(True), "fts5-trigram")
        self.assertEqual(lexical_index.mode_label(False), "substring-scan")

    def test_write_and_narrow_by_exact_id_alias_and_path(self):
        lexical_index.create_tables(self.conn, trigram=True)
        doc = _doc("a", hydra_id="hydra://knowledge-unit/example", aliases=("hydra://alias/example",), path="a.md", title="Example")
        self._insert_document_row(doc)
        lexical_index.write_rows(self.conn, [doc], trigram=True, slugify=slugify, normal_path=_normal_path)

        self.assertEqual(lexical_index.narrow_by_exact(self.conn, {"hydra://knowledge-unit/example"}, ""), {"a"})
        self.assertEqual(lexical_index.narrow_by_exact(self.conn, {"hydra://alias/example"}, ""), {"a"})
        self.assertEqual(lexical_index.narrow_by_exact(self.conn, {"a.md"}, ""), {"a"})
        self.assertEqual(lexical_index.narrow_by_exact(self.conn, {"nothing-like-this"}, ""), set())

    def test_write_and_narrow_by_slug(self):
        lexical_index.create_tables(self.conn, trigram=True)
        doc = _doc("a", title="Example Package", package="example", routes=("fix_provider_surface",), keywords=("adapter exports",))
        self._insert_document_row(doc)
        lexical_index.write_rows(self.conn, [doc], trigram=True, slugify=slugify, normal_path=_normal_path)

        self.assertEqual(lexical_index.narrow_by_exact(self.conn, set(), slugify("Example Package")), {"a"})
        self.assertEqual(lexical_index.narrow_by_exact(self.conn, set(), slugify("fix_provider_surface")), {"a"})
        self.assertEqual(lexical_index.narrow_by_exact(self.conn, set(), slugify("adapter exports")), {"a"})
        self.assertEqual(lexical_index.narrow_by_exact(self.conn, set(), slugify("no such slug at all")), set())

    def test_write_and_narrow_by_terms_via_fts5_trigram(self):
        lexical_index.create_tables(self.conn, trigram=True)
        first = _doc("a", path="a.md", title="Alpha", body="hydra routing adapter exports")
        second = _doc("b", path="b.md", title="Beta", body="nothing relevant here")
        for doc in (first, second):
            self._insert_document_row(doc)
        lexical_index.write_rows(self.conn, [first, second], trigram=True, slugify=slugify, normal_path=_normal_path)

        self.assertEqual(lexical_index.narrow_by_terms(self.conn, ["adapter"]), {"a"})
        self.assertEqual(lexical_index.narrow_by_terms(self.conn, ["exports", "nothing"]), {"a", "b"})
        self.assertEqual(lexical_index.narrow_by_terms(self.conn, ["absolutely-nowhere"]), set())
        self.assertEqual(lexical_index.narrow_by_terms(self.conn, []), set())

    def test_no_fts5_table_when_trigram_unsupported(self):
        lexical_index.create_tables(self.conn, trigram=False)
        doc = _doc("a", title="Example", body="adapter exports")
        self._insert_document_row(doc)
        lexical_index.write_rows(self.conn, [doc], trigram=False, slugify=slugify, normal_path=_normal_path)
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute("SELECT * FROM documents_fts")
        # Exact/slug lookups are unconditional and still work.
        self.assertEqual(lexical_index.narrow_by_exact(self.conn, set(), slugify("Example")), {"a"})

    def test_delete_rows_for_keys_removes_from_every_table(self):
        lexical_index.create_tables(self.conn, trigram=True)
        doc = _doc("a", hydra_id="hydra://knowledge-unit/example", path="a.md", title="Example", body="adapter exports")
        self._insert_document_row(doc)
        lexical_index.write_rows(self.conn, [doc], trigram=True, slugify=slugify, normal_path=_normal_path)

        lexical_index.delete_rows_for_keys(self.conn, ["a"], trigram=True)

        self.assertEqual(lexical_index.narrow_by_exact(self.conn, {"hydra://knowledge-unit/example"}, ""), set())
        self.assertEqual(lexical_index.narrow_by_exact(self.conn, set(), slugify("Example")), set())
        self.assertEqual(lexical_index.narrow_by_terms(self.conn, ["adapter"]), set())

    def test_delete_rows_for_keys_is_a_noop_for_an_empty_key_list(self):
        lexical_index.create_tables(self.conn, trigram=True)
        lexical_index.delete_rows_for_keys(self.conn, [], trigram=True)  # must not raise

    def test_keys_for_paths(self):
        first = _doc("a", path="a.md")
        second = _doc("b", path="b.md")
        for doc in (first, second):
            self._insert_document_row(doc)
        self.assertEqual(set(lexical_index.keys_for_paths(self.conn, ["a.md", "b.md"])), {"a", "b"})
        self.assertEqual(lexical_index.keys_for_paths(self.conn, []), [])
        self.assertEqual(lexical_index.keys_for_paths(self.conn, ["missing.md"]), [])

    def test_read_documents_by_keys_returns_only_the_requested_keys(self):
        for key in ("b", "a", "c"):
            self._insert_document_row(_doc(key, path=f"{key}.md"))
        rows = lexical_index.read_documents_by_keys(self.conn, ["a", "c"], lambda row: row[0])
        self.assertEqual(set(rows), {"a", "c"})
        self.assertEqual(lexical_index.read_documents_by_keys(self.conn, [], lambda row: row[0]), [])


if __name__ == "__main__":
    unittest.main()
