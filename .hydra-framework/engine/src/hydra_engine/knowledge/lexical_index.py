"""Real lexical index maintenance and candidate narrowing (P13/P14, D10).

An FTS5 table (trigram tokenizer) plus small exact-selector lookup tables,
maintained inside the same write transactions as `documents`. These narrow a
query to a small candidate set; `search_index` still computes channel, rank,
graph count and the tie-break over that narrowed set with its existing,
unchanged code. A host whose SQLite lacks the trigram tokenizer gets no
narrowing at all -- `search_index` falls back to its whole-corpus scan -- so
a mismatch here can never produce a wrong answer, only a slower one.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable

TABLE_NAMES = ("documents_fts", "document_ids", "document_paths", "document_slugs")


def mode_label(trigram: bool) -> str:
    return "fts5-trigram" if trigram else "substring-scan"


def create_tables(conn: sqlite3.Connection, *, trigram: bool) -> None:
    conn.execute("CREATE TABLE document_ids (value TEXT, key TEXT)")
    conn.execute("CREATE INDEX idx_document_ids_value ON document_ids(value)")
    conn.execute("CREATE TABLE document_paths (value TEXT, key TEXT)")
    conn.execute("CREATE INDEX idx_document_paths_value ON document_paths(value)")
    conn.execute("CREATE TABLE document_slugs (value TEXT, key TEXT)")
    conn.execute("CREATE INDEX idx_document_slugs_value ON document_slugs(value)")
    if trigram:
        conn.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(key UNINDEXED, haystack, tokenize='trigram')")


def _haystack(doc) -> str:
    return "\n".join([
        doc.hydra_id, " ".join(doc.aliases), doc.path, doc.kind, doc.package,
        doc.title, " ".join(doc.keywords), " ".join(doc.routes),
        " ".join(doc.use_when), " ".join(doc.headings), doc.body,
    ]).lower()


def _slug_values(doc, slugify: Callable[[str], str]) -> set[str]:
    values = {slugify(doc.title), slugify(doc.package)}
    values.update(slugify(route) for route in doc.routes)
    values.update(slugify(keyword) for keyword in doc.keywords)
    values.discard("")
    return values


def write_rows(conn: sqlite3.Connection, docs: list, *, trigram: bool, slugify: Callable[[str], str], normal_path: Callable[[str], str]) -> None:
    id_rows: list[tuple[str, str]] = []
    path_rows: list[tuple[str, str]] = []
    slug_rows: list[tuple[str, str]] = []
    fts_rows: list[tuple[str, str]] = []
    for doc in docs:
        if doc.hydra_id:
            id_rows.append((doc.hydra_id.lower(), doc.key))
        id_rows.extend((alias.lower(), doc.key) for alias in doc.aliases if alias)
        if doc.path:
            path_rows.append((normal_path(doc.path), doc.key))
        slug_rows.extend((value, doc.key) for value in _slug_values(doc, slugify))
        if trigram:
            fts_rows.append((doc.key, _haystack(doc)))
    conn.executemany("INSERT INTO document_ids VALUES (?, ?)", id_rows)
    conn.executemany("INSERT INTO document_paths VALUES (?, ?)", path_rows)
    conn.executemany("INSERT INTO document_slugs VALUES (?, ?)", slug_rows)
    if trigram:
        conn.executemany("INSERT INTO documents_fts VALUES (?, ?)", fts_rows)


def delete_rows_for_keys(conn: sqlite3.Connection, keys: Iterable[str], *, trigram: bool) -> None:
    keys = tuple(keys)
    if not keys:
        return
    placeholders = ", ".join("?" for _ in keys)
    for table in ("document_ids", "document_paths", "document_slugs"):
        conn.execute(f"DELETE FROM {table} WHERE key IN ({placeholders})", keys)
    if trigram:
        conn.execute(f"DELETE FROM documents_fts WHERE key IN ({placeholders})", keys)


def keys_for_paths(conn: sqlite3.Connection, paths: Iterable[str]) -> list[str]:
    paths = tuple(paths)
    if not paths:
        return []
    placeholders = ", ".join("?" for _ in paths)
    return [row[0] for row in conn.execute(f"SELECT key FROM documents WHERE path IN ({placeholders})", paths)]


def narrow_by_exact(conn: sqlite3.Connection, wanted: set[str], query_slug: str) -> set[str]:
    keys: set[str] = set()
    if wanted:
        placeholders = ", ".join("?" for _ in wanted)
        values = tuple(wanted)
        keys.update(row[0] for row in conn.execute(f"SELECT DISTINCT key FROM document_ids WHERE value IN ({placeholders})", values))
        keys.update(row[0] for row in conn.execute(f"SELECT DISTINCT key FROM document_paths WHERE value IN ({placeholders})", values))
    if query_slug:
        keys.update(row[0] for row in conn.execute("SELECT DISTINCT key FROM document_slugs WHERE value = ?", (query_slug,)))
    return keys


def narrow_by_terms(conn: sqlite3.Connection, terms: list[str]) -> set[str]:
    """Candidate keys whose haystack contains any *term* as a literal
    substring, via an FTS5 trigram phrase-per-term OR query. Only valid
    against an index built with the trigram tokenizer."""
    if not terms:
        return set()
    match_expr = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
    return {row[0] for row in conn.execute("SELECT DISTINCT key FROM documents_fts WHERE documents_fts MATCH ?", (match_expr,))}


def read_documents_by_keys(conn: sqlite3.Connection, keys: Iterable[str], decode: Callable[[tuple], object]) -> list:
    keys = tuple(keys)
    if not keys:
        return []
    placeholders = ", ".join("?" for _ in keys)
    rows = conn.execute(f"SELECT * FROM documents WHERE key IN ({placeholders}) ORDER BY rowid", keys)
    return [decode(row) for row in rows]
