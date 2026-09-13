"""Deterministic local knowledge search."""

from __future__ import annotations

import dataclasses
import re
import sqlite3
from pathlib import Path

from hydra_engine.documents.tokens import display_path, is_relative_to
from hydra_engine.identity.slugs import slugify
from hydra_engine.knowledge.candidates import APPROX_CHARS_PER_TOKEN, approx_tokens
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.knowledge import index_cache, index_collection
from hydra_engine.telemetry.writer import event_growth_notes as knowledge_events_growth_notes, events_path as telemetry_events_path, knowledge_counts as telemetry_counts, record_knowledge_command_usage as record_command_usage, record_knowledge_route as record_route

SCHEMA_VERSION = "hydra-framework.knowledge-store.v3"
DEFAULT_RESULT_LIMIT = 20
DEFAULT_BUDGET = 2000
DEFAULT_PREVIEW_CHARS = 280
_TOKEN_RE = re.compile(r"[0-9A-Za-z_./:-]+")
_HYDRA_URI_RE = re.compile(r"hydra://[A-Za-z0-9_./:-]+")
_PATH_RE = re.compile(r"(?:^|\s)([.]?/?(?:AI_SYSTEM\.md|\.hydra-framework/[^\s`'\",)]+|project-wiki/[^\s`'\",)]+))")
_DOCUMENT_COLUMNS = ("key", "hydra_id", "aliases", "path", "kind", "package", "title", "keywords", "routes", "use_when", "headings", "body", "relations", "content_id")

@dataclasses.dataclass(frozen=True)
class SqliteFeatures:
    fts5: bool; trigram: bool; error: str = ""

SearchDocument = index_collection.SearchDocument

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
    def citation(self) -> str: return self.document.path


default_db_path = index_cache.default_db_path
fingerprint = index_cache.fingerprint

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
collect_search_documents = index_collection.collect_search_documents


def build_index(paths: ContextCompilerPaths, resolver_paths: ObjectLocations, local: Path, command_ids: tuple[str, ...] = ()) -> tuple[int, SqliteFeatures]:
    try:
        content_ids = fingerprint(paths.root)
    except index_cache.FreshnessError:
        content_ids = {}
    docs = collect_search_documents(paths, resolver_paths, command_ids, content_ids=content_ids)
    features = probe_sqlite_features()

    def populate(conn: sqlite3.Connection) -> None:
        storage = __import__("hydra_engine.knowledge.storage", fromlist=("write_sqlite_store",))
        storage.write_sqlite_store(conn, index_collection.build_knowledge_store(paths))
        _write_documents(conn, docs)
        _write_meta(conn, command_ids, features)

    index_cache.rebuild_index(local, populate)
    return len(docs), features


def _write_documents(conn: sqlite3.Connection, docs: list[SearchDocument]) -> None:
    index_cache.write_documents(conn, docs, _row_for_document)


def _write_meta(conn: sqlite3.Connection, command_ids: tuple[str, ...], features: SqliteFeatures) -> None:
    index_cache.write_meta(conn, command_ids, features, SCHEMA_VERSION)
def index_status(paths: ContextCompilerPaths, resolver_paths: ObjectLocations, local: Path, command_ids: tuple[str, ...] = ()) -> str:
    state = _cache_state(paths, local)
    if isinstance(state, index_cache.SourceOnly):
        return "source"
    if isinstance(state, index_cache.Absent):
        return "missing"
    return "fresh" if isinstance(state, index_cache.Fresh) and index_cache.command_ids_match(state.db_path, command_ids) else "stale"


def _cache_state(paths: ContextCompilerPaths, local: Path) -> index_cache.CacheState:
    return index_cache.cache_state(
        paths, local, guard=index_cache.guard_for(paths.root.resolve()),
        schema=SCHEMA_VERSION, columns=_DOCUMENT_COLUMNS,
    )


def _update_index(paths, resolver_paths, local: Path, command_ids: tuple[str, ...], state: index_cache.Stale) -> Path:
    changed = tuple(sorted(set((*state.delta.added, *state.delta.modified))))
    removed = tuple(sorted(set((*state.delta.deleted, *state.delta.modified))))

    def apply_update(conn: sqlite3.Connection, current: dict[str, str]) -> None:
        nodes = index_collection.discover_nodes_or_empty(paths)
        docs = collect_search_documents(paths, resolver_paths, content_ids=current, only_paths=frozenset(changed), _nodes=nodes)
        replacements = index_collection.collect_changed_knowledge_objects(paths, changed, _nodes=nodes)
        if removed:
            conn.execute(f"DELETE FROM documents WHERE path IN ({', '.join('?' for _ in removed)})", removed)
        _write_documents(conn, docs)
        index_cache.replace_changed_knowledge_rows(conn, removed, replacements)

    return index_cache.apply_index_delta(
        paths, local, expected_generation=state.generation or "",
        expected_fingerprint=state.fingerprint, apply_update=apply_update,
    )

def search(
    query: str,
    *,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    local: Path,
    command_ids: tuple[str, ...] = (),
    path_refs: tuple[str, ...] = (),
    limit: int = DEFAULT_RESULT_LIMIT,
    force_source: bool = False,
) -> tuple[list[SearchResult], SqliteFeatures, str]:
    state: index_cache.CacheState = index_cache.SourceOnly("force-source") if force_source else _cache_state(paths, local)
    try:
        if isinstance(state, index_cache.Stale) and index_cache.command_ids_match(state.db_path, command_ids):
            if index_collection.delta_is_local(paths, resolver_paths, state.delta):
                _update_index(paths, resolver_paths, local, command_ids, state)
            else:
                build_index(paths, resolver_paths, local, command_ids)
            state = _cache_state(paths, local)
        elif isinstance(state, index_cache.Absent) or (isinstance(state, index_cache.Fresh) and not index_cache.command_ids_match(state.db_path, command_ids)):
            build_index(paths, resolver_paths, local, command_ids)
            state = _cache_state(paths, local)
    except (OSError, sqlite3.Error, ValueError):
        state = index_cache.SourceOnly("index-update-failed")
    if isinstance(state, index_cache.Fresh):
        docs = _load_documents(state.db_path)
        source = "sqlite" if docs is not None else "source"
    else:
        docs = None
        source = "source"
    if docs is None:
        docs = collect_search_documents(paths, resolver_paths, command_ids)
    docs = _with_explicit_path_docs(docs, query, path_refs, paths, resolver_paths)
    exact = exact_matches(query, docs, path_refs)
    if source == "sqlite" and not exact and _has_explicit_selector(query, path_refs):
        # A cache may legitimately miss an implicit ranking candidate, but an
        # explicit id/path is an authority request and must never be answered
        # from a derived negative.
        return _search_from_canonical_snapshot(query, paths, resolver_paths, command_ids, path_refs, limit)
    if exact:
        exact = _hydrate_cached_candidates(exact[:limit], paths, state.db_path if isinstance(state, index_cache.Fresh) else None, source)
        if exact is None:
            return _search_from_canonical_snapshot(query, paths, resolver_paths, command_ids, path_refs, limit)
        return exact, probe_sqlite_features(), source
    features = probe_sqlite_features()
    results = substring_search(query, docs)[:limit]
    hydrated = _hydrate_cached_candidates(results, paths, state.db_path if isinstance(state, index_cache.Fresh) else None, source)
    if hydrated is None:
        return _search_from_canonical_snapshot(query, paths, resolver_paths, command_ids, path_refs, limit)
    return hydrated, features, source
def _search_from_canonical_snapshot(
    query: str, paths: ContextCompilerPaths, resolver_paths: ObjectLocations, command_ids: tuple[str, ...],
    path_refs: tuple[str, ...], limit: int,
) -> tuple[list[SearchResult], SqliteFeatures, str]:
    """Abandon a cache operation rather than mixing cached and source graphs."""
    docs = _with_explicit_path_docs(
        collect_search_documents(paths, resolver_paths, command_ids), query, path_refs, paths, resolver_paths,
    )
    exact = exact_matches(query, docs, path_refs)
    features = probe_sqlite_features()
    return (exact or substring_search(query, docs))[:limit], features, "source"
def _hydrate_cached_candidates(results: list[SearchResult], paths: ContextCompilerPaths, db_path: Path | None, source: str) -> list[SearchResult] | None:
    storage = __import__("hydra_engine.knowledge.storage", fromlist=("hydrate_search_candidates",))
    return storage.hydrate_search_candidates(paths, db_path, results) if source == "sqlite" and db_path is not None else results
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
            results.append(SearchResult(doc, "exact", 0, sum(value.startswith("hydra://knowledge-package/") for value in doc.relations)))
        elif query_slug and query_slug in names | command_names:
            results.append(SearchResult(doc, "exact", 0, sum(value.startswith("hydra://knowledge-package/") for value in doc.relations)))
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
            results.append(SearchResult(doc, channel, -hits, sum(value.startswith("hydra://knowledge-package/") for value in doc.relations)))
    return sorted_results(results)
def sorted_results(results: list[SearchResult]) -> list[SearchResult]:
    tier = {"exact": 0, "path-route": 1, "substring": 2}
    return sorted(results, key=lambda r: (tier.get(r.channel, 9), r.rank, -r.graph_count, r.document.hydra_id, r.document.path))
def _load_documents(db_path: Path | None) -> list[SearchDocument] | None:
    return index_cache.load_documents(
        db_path, schema=SCHEMA_VERSION, columns=_DOCUMENT_COLUMNS,
        decode=_document_from_row,
    )

def _with_explicit_path_docs(docs: list[SearchDocument], query: str, path_refs: tuple[str, ...], paths: ContextCompilerPaths, resolver_paths: ObjectLocations) -> list[SearchDocument]:
    by_path = {_normal_path(doc.path): doc for doc in docs}
    nodes = None
    for raw in [*path_refs, *[match.group(1) for match in _PATH_RE.finditer(query)]]:
        path = paths.root / _normal_path(raw)
        if not path.is_file() or not is_relative_to(path, paths.root):
            continue
        rel = _normal_path(display_path(path, paths.root))
        if rel not in by_path:
            if nodes is None:
                nodes = index_collection.discover_nodes_or_empty(paths)
            by_path[rel] = index_collection.document_for_path(paths, path, rel, "", {}, nodes)
    return list(by_path.values())
def _row_for_document(doc: SearchDocument) -> tuple:
    return (
        doc.key, doc.hydra_id, "\n".join(doc.aliases), doc.path, doc.kind, doc.package,
        doc.title, "\n".join(doc.keywords), "\n".join(doc.routes), "\n".join(doc.use_when),
        "\n".join(doc.headings), doc.body, "\n".join(doc.relations), doc.content_id,
    )
def _document_from_row(row: tuple) -> SearchDocument:
    return SearchDocument(
        key=row[0], hydra_id=row[1], aliases=tuple(row[2].splitlines()), path=row[3], kind=row[4],
        package=row[5], title=row[6], keywords=tuple(row[7].splitlines()), routes=tuple(row[8].splitlines()),
        use_when=tuple(row[9].splitlines()), headings=tuple(row[10].splitlines()), body=row[11],
        relations=tuple(row[12].splitlines()), content_id=row[13],
    )
def _normal_path(value: str) -> str:
    return value.strip().lstrip("./")
def _has_explicit_selector(query: str, path_refs: tuple[str, ...]) -> bool:
    return bool(path_refs or _HYDRA_URI_RE.search(query) or _PATH_RE.search(query))
