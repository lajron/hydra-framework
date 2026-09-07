"""Deterministic local knowledge search."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import sqlite3
from pathlib import Path

from hydra_engine.documents.markdown import strip_markdown_code_fences
from hydra_engine.documents.tokens import display_path, is_relative_to, read_text
from hydra_engine.identity.slugs import slugify
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN, approx_tokens
from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes, knowledge_node_for_path, resolve_inheritance
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.objects.registry import registry_object_entries
from hydra_engine.telemetry.writer import event_growth_notes as knowledge_events_growth_notes, events_path as telemetry_events_path, knowledge_counts as telemetry_counts, record_knowledge_command_usage as record_command_usage, record_knowledge_route as record_route

SCHEMA_VERSION = "hydra-framework.knowledge-search.v1"
DEFAULT_RESULT_LIMIT = 20
DEFAULT_BUDGET = 2000
DEFAULT_PREVIEW_CHARS = 280
SEARCH_EXTENSIONS = {".md", ".yaml", ".yml", ".txt", ".sh", ".py"}
SEARCH_ROOTS = (".hydra-framework/repo/knowledge", ".hydra-framework/capabilities", ".hydra-framework/core", ".hydra-framework/validation", ".hydra-framework/engine/src/hydra_engine")
_TOKEN_RE = re.compile(r"[0-9A-Za-z_./:-]+")
_HYDRA_URI_RE = re.compile(r"hydra://[A-Za-z0-9_./:-]+")
_PATH_RE = re.compile(r"(?:^|\s)([.]?/?(?:AI_SYSTEM\.md|\.hydra-framework/[^\s`'\",)]+|project-wiki/[^\s`'\",)]+))")
_DOCUMENT_COLUMNS = ("key", "hydra_id", "aliases", "path", "kind", "package", "title", "keywords", "routes", "use_when", "headings", "body", "relations")
_SQLITE_BUSY_TIMEOUT_MS = 5000

def _connect(db_path: Path) -> sqlite3.Connection:
    """WAL mode lets a concurrent reader keep working through the DROP-and-
    rebuild in `build_index`; `busy_timeout` waits out a writer instead of
    raising `database is locked`."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
    return conn

@dataclasses.dataclass(frozen=True)
class SqliteFeatures:
    fts5: bool; trigram: bool; error: str = ""

@dataclasses.dataclass(frozen=True)
class SearchDocument:
    key: str; hydra_id: str; aliases: tuple[str, ...]; path: str; kind: str; package: str; title: str
    keywords: tuple[str, ...]; routes: tuple[str, ...]; use_when: tuple[str, ...]; headings: tuple[str, ...]
    body: str; relations: tuple[str, ...]

@dataclasses.dataclass(frozen=True)
class SearchResult:
    document: SearchDocument; channel: str; rank: float
    graph_count: int = 0

    @property
    def approx_tokens(self) -> int: return self.approx_token_count()

    @property
    def snippet(self) -> str: return self.snippet_text()

    def approx_token_count(self, chars_per_token: int = APPROX_CHARS_PER_TOKEN, preview_chars: int = DEFAULT_PREVIEW_CHARS) -> int:
        return approx_tokens(self.snippet_text(preview_chars), chars_per_token)

    def snippet_text(self, preview_chars: int = DEFAULT_PREVIEW_CHARS) -> str:
        text = self.document.body.strip()
        return text if len(text) <= preview_chars else text[:preview_chars].rstrip() + " ..."
    def citation(self) -> str:
        return self.document.path


def default_db_path(local: Path) -> Path: return local / "index" / "knowledge.db"

def probe_sqlite_features() -> SqliteFeatures:
    try:
        with sqlite3.connect(":memory:") as conn:
            conn.execute("CREATE VIRTUAL TABLE probe USING fts5(value)")
            trigram = True
            try:
                conn.execute("CREATE VIRTUAL TABLE probe_tri USING fts5(value, tokenize='trigram')")
            except sqlite3.Error:
                trigram = False
            return SqliteFeatures(fts5=True, trigram=trigram)
    except sqlite3.Error as error:
        return SqliteFeatures(fts5=False, trigram=False, error=str(error))

def collect_search_documents(
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    command_ids: tuple[str, ...] = (),
) -> list[SearchDocument]:
    registry, _errors = registry_object_entries(resolver_paths.object_registry, resolver_paths.root)
    by_path: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    for hydra_id, entry in registry.items():
        by_id[hydra_id] = entry
        path = _str(entry.get("path"))
        if path:
            by_path.setdefault(path, {"ids": [], "entries": []})
            by_path[path]["ids"].append(hydra_id)
            by_path[path]["entries"].append(entry)

    docs: dict[str, SearchDocument] = {}
    for file_path in _search_files(paths.root):
        rel = display_path(file_path, paths.root)
        grouped = by_path.get(rel, {"ids": [], "entries": []})
        entry = grouped["entries"][0] if grouped["entries"] else {}
        hydra_id = grouped["ids"][0] if grouped["ids"] else ""
        docs[rel] = _document_for_path(paths, resolver_paths, file_path, rel, hydra_id, entry)

    for hydra_id, entry in by_id.items():
        path = _str(entry.get("path"))
        if path not in docs:
            docs[f"id:{hydra_id}"] = _document_for_registry_entry(paths, hydra_id, entry)

    for command_id in command_ids:
        key = f"command:{command_id}"
        docs[key] = SearchDocument(
            key=key, hydra_id="", aliases=(), path="", kind="command", package="",
            title=command_id, keywords=(command_id,), routes=(), use_when=(),
            headings=(), body=f"hydra.py {command_id}", relations=(),
        )
    return list(docs.values())

def build_index(
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    local: Path,
    command_ids: tuple[str, ...] = (),
) -> tuple[int, SqliteFeatures]:
    docs = collect_search_documents(paths, resolver_paths, command_ids)
    features = probe_sqlite_features()
    db_path = default_db_path(local)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS documents")
        conn.execute("DROP TABLE IF EXISTS meta")
        conn.execute("DROP TABLE IF EXISTS docs_fts")
        conn.execute(
            "CREATE TABLE documents (key TEXT PRIMARY KEY, hydra_id TEXT, aliases TEXT, path TEXT, kind TEXT, "
            "package TEXT, title TEXT, keywords TEXT, routes TEXT, use_when TEXT, headings TEXT, body TEXT, relations TEXT)"
        )
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.executemany(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [_row_for_document(doc) for doc in docs],
        )
        if features.fts5:
            tokenizer = "tokenize='trigram'" if features.trigram else ""
            conn.execute(
                "CREATE VIRTUAL TABLE docs_fts USING fts5("
                "hydra_id, aliases, path, kind, package, title, keywords, routes, use_when, headings, body"
                f"{', ' + tokenizer if tokenizer else ''})"
            )
            conn.executemany(
                "INSERT INTO docs_fts(rowid, hydra_id, aliases, path, kind, package, title, keywords, routes, use_when, headings, body) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(index, *(_row_for_document(doc)[1:12])) for index, doc in enumerate(docs, start=1)],
            )
        conn.executemany(
            "INSERT INTO meta VALUES (?, ?)",
            [
                ("schema", SCHEMA_VERSION),
                ("fts5", "yes" if features.fts5 else "no"),
                ("trigram", "yes" if features.trigram else "no"),
                ("digest", _corpus_digest(docs)),
            ],
        )
    return len(docs), features


def index_status(paths: ContextCompilerPaths, resolver_paths: ObjectLocations, local: Path, command_ids: tuple[str, ...] = ()) -> str:
    db_path = default_db_path(local)
    if not db_path.exists(): return "missing"
    docs = collect_search_documents(paths, resolver_paths, command_ids)
    return "fresh" if _load_documents(db_path, _corpus_digest(docs)) else "stale"


def search(
    query: str,
    *,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    local: Path,
    command_ids: tuple[str, ...] = (),
    path_refs: tuple[str, ...] = (),
    limit: int = DEFAULT_RESULT_LIMIT,
) -> tuple[list[SearchResult], SqliteFeatures, str]:
    source_docs = collect_search_documents(paths, resolver_paths, command_ids)
    docs = _load_documents(default_db_path(local), _corpus_digest(source_docs))
    source = "sqlite" if docs else "source"
    if not docs:
        docs = source_docs
    docs = _with_explicit_path_docs(docs, query, path_refs, paths, resolver_paths)
    exact = exact_matches(query, docs, path_refs)
    if exact:
        return exact[:limit], probe_sqlite_features(), source
    features = probe_sqlite_features()
    if features.fts5 and source == "sqlite":
        results = _fts_search(default_db_path(local), query, docs, limit)
        if results:
            return results[:limit], features, source
    return substring_search(query, docs)[:limit], features, source

def exact_matches(query: str, docs: list[SearchDocument], path_refs: tuple[str, ...] = ()) -> list[SearchResult]:
    wanted = {value.lower().strip() for value in _HYDRA_URI_RE.findall(query)}
    wanted.update(_normal_path(value) for value in path_refs if value)
    wanted.update(_normal_path(match.group(1)) for match in _PATH_RE.finditer(query))
    query_slug = slugify(query.strip())
    results: list[SearchResult] = []
    for doc in docs:
        ids = {doc.hydra_id.lower(), *[alias.lower() for alias in doc.aliases]}
        paths = {_normal_path(doc.path)}
        names = {slugify(doc.title), slugify(doc.package), *[slugify(route) for route in doc.routes], *[slugify(keyword) for keyword in doc.keywords]}
        command_names = {slugify(doc.title)} if doc.kind == "command" else set()
        if wanted & ids or wanted & paths:
            results.append(SearchResult(doc, "exact", 0, graph_relation_count(doc)))
        elif query_slug and query_slug in names | command_names:
            results.append(SearchResult(doc, "exact", 0, graph_relation_count(doc)))
    return sorted_results(results)

def substring_search(query: str, docs: list[SearchDocument]) -> list[SearchResult]:
    terms = [token.lower() for token in _TOKEN_RE.findall(query) if len(token) > 2]
    results: list[SearchResult] = []
    for doc in docs:
        haystack = "\n".join([
            doc.hydra_id, " ".join(doc.aliases), doc.path, doc.kind, doc.package,
            doc.title, " ".join(doc.keywords), " ".join(doc.routes),
            " ".join(doc.use_when), " ".join(doc.headings), doc.body,
        ]).lower()
        hits = sum(1 for term in terms if term in haystack)
        if hits:
            channel = "path-route" if any(term in f"{doc.path} {' '.join(doc.routes)}".lower() for term in terms) else "substring"
            results.append(SearchResult(doc, channel, -hits, graph_relation_count(doc)))
    return sorted_results(results)

def sorted_results(results: list[SearchResult]) -> list[SearchResult]:
    tier = {"exact": 0, "path-route": 1, "fts": 2, "substring": 3}
    return sorted(results, key=lambda r: (tier.get(r.channel, 9), r.rank, -r.graph_count, r.document.hydra_id, r.document.path))

def package_votes(results: list[SearchResult]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for result in results:
        package = result.document.package
        if package:
            counts[package] = counts.get(package, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))

def graph_relation_count(doc: SearchDocument) -> int:
    return sum(1 for relation in doc.relations if relation.startswith("hydra://knowledge-package/"))

def _fts_search(db_path: Path, query: str, docs: list[SearchDocument], limit: int = DEFAULT_RESULT_LIMIT) -> list[SearchResult]:
    expression = _fts_query(query)
    if not expression:
        return []
    by_rowid = {index: doc for index, doc in enumerate(docs, start=1)}
    try:
        with _connect(db_path) as conn:
            rows = conn.execute(
                "SELECT rowid, bm25(docs_fts, 12.0, 10.0, 9.0, 4.0, 8.0, 7.0, 6.0, 6.0, 5.0, 3.0, 1.0) AS rank "
                "FROM docs_fts WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?",
                (expression, max(limit, 1) * 2),
            ).fetchall()
    except sqlite3.Error:
        return []
    return sorted_results([SearchResult(by_rowid[rowid], "fts", float(rank), graph_relation_count(by_rowid[rowid])) for rowid, rank in rows if rowid in by_rowid])

def _fts_query(query: str) -> str:
    tokens = [token.strip(":/.-_").lower() for token in _TOKEN_RE.findall(query)]
    useful = [token for token in tokens if len(token) > 1]
    return " OR ".join(f'"{token}"' for token in useful)

def _load_documents(db_path: Path, expected_digest: str) -> list[SearchDocument]:
    if not db_path.exists():
        return []
    try:
        with _connect(db_path) as conn:
            meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
            columns = [row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()]
            if meta.get("schema") != SCHEMA_VERSION or meta.get("digest") != expected_digest or columns != list(_DOCUMENT_COLUMNS):
                return []
            rows = conn.execute("SELECT * FROM documents ORDER BY rowid").fetchall()
            return [_document_from_row(row) for row in rows]
    except (IndexError, sqlite3.Error):
        return []

def _search_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for raw in SEARCH_ROOTS:
        base = root / raw
        if not base.exists():
            continue
        files.extend(path for path in sorted(base.rglob("*")) if path.is_file() and path.suffix in SEARCH_EXTENSIONS)
    if (root / "AI_SYSTEM.md").exists():
        files.append(root / "AI_SYSTEM.md")
    return sorted(set(files))

def _with_explicit_path_docs(docs: list[SearchDocument], query: str, path_refs: tuple[str, ...], paths: ContextCompilerPaths, resolver_paths: ObjectLocations) -> list[SearchDocument]:
    by_path = {_normal_path(doc.path): doc for doc in docs}
    for raw in [*path_refs, *[match.group(1) for match in _PATH_RE.finditer(query)]]:
        path = paths.root / _normal_path(raw)
        if not path.is_file() or not is_relative_to(path, paths.root):
            continue
        rel = _normal_path(display_path(path, paths.root))
        if rel not in by_path:
            by_path[rel] = _document_for_path(paths, resolver_paths, path, rel, "", {})
    return list(by_path.values())


def _document_for_path(paths: ContextCompilerPaths, resolver_paths: ObjectLocations, file_path: Path, rel: str, hydra_id: str, entry: dict) -> SearchDocument:
    text = read_text(file_path)
    headings = tuple(line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#"))
    package = _package_for(file_path, paths, hydra_id, entry)
    routes, use_when, keywords = _routing_fields(file_path, paths, resolver_paths)
    return SearchDocument(
        key=rel, hydra_id=hydra_id, aliases=tuple(_list(entry.get("aliases"))), path=rel,
        kind=_str(entry.get("kind"), "file"), package=package,
        title=_str(entry.get("title"), headings[0] if headings else file_path.stem),
        keywords=keywords, routes=routes, use_when=use_when, headings=headings,
        body=strip_markdown_code_fences(text), relations=tuple(_list(entry.get("relations"))),
    )


def _document_for_registry_entry(paths: ContextCompilerPaths, hydra_id: str, entry: dict) -> SearchDocument:
    path = _str(entry.get("path"))
    return SearchDocument(
        key=f"id:{hydra_id}", hydra_id=hydra_id, aliases=tuple(_list(entry.get("aliases"))),
        path=path, kind=_str(entry.get("kind")), package=_package_for(paths.root / path, paths, hydra_id, entry),
        title=_str(entry.get("title")), keywords=(), routes=(), use_when=(),
        headings=(), body=_str(entry.get("title")), relations=tuple(_list(entry.get("relations"))),
    )


def _package_for(file_path: Path, paths: ContextCompilerPaths, hydra_id: str, entry: dict) -> str:
    for prefix in ("hydra://knowledge-space/", "hydra://knowledge-node/"):
        if hydra_id.startswith(prefix):
            return hydra_id.removeprefix(prefix)
    try:
        nodes = discover_knowledge_nodes(paths)
    except Exception:
        return ""
    node = knowledge_node_for_path(file_path, nodes, paths)
    return node.logical_id if node else ""


def _routing_fields(file_path: Path, paths: ContextCompilerPaths, resolver_paths: ObjectLocations) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    try:
        nodes = discover_knowledge_nodes(paths)
    except Exception:
        return (), (), ()
    node = knowledge_node_for_path(file_path, nodes, paths)
    if node is None:
        return (), (), ()
    routes = resolve_inheritance(node, {item.logical_id: item for item in nodes})["routes"]
    return tuple(routes), tuple(value for route in routes.values() for value in route.use_when), node.keywords


def _row_for_document(doc: SearchDocument) -> tuple:
    return (
        doc.key, doc.hydra_id, "\n".join(doc.aliases), doc.path, doc.kind, doc.package,
        doc.title, "\n".join(doc.keywords), "\n".join(doc.routes), "\n".join(doc.use_when),
        "\n".join(doc.headings), doc.body, "\n".join(doc.relations),
    )


def _document_from_row(row: tuple) -> SearchDocument:
    return SearchDocument(
        key=row[0], hydra_id=row[1], aliases=tuple(row[2].splitlines()), path=row[3], kind=row[4],
        package=row[5], title=row[6], keywords=tuple(row[7].splitlines()), routes=tuple(row[8].splitlines()),
        use_when=tuple(row[9].splitlines()), headings=tuple(row[10].splitlines()), body=row[11],
        relations=tuple(row[12].splitlines()),
    )


def _corpus_digest(docs: list[SearchDocument]) -> str:
    digest = hashlib.sha256()
    for doc in sorted(docs, key=lambda item: item.key):
        digest.update(repr(_row_for_document(doc)).encode("utf-8"))
    return digest.hexdigest()


def _normal_path(value: str) -> str:
    return value.strip().lstrip("./")


def _list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _map(value: object) -> dict: return value if isinstance(value, dict) else {}


def _str(value: object, default: str = "") -> str: return str(value) if value is not None else default
