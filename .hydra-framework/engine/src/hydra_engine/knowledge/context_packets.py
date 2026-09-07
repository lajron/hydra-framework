"""Deterministic Knowledge v3 context-packet compilation."""

from __future__ import annotations

from hydra_engine.knowledge.candidates import (
    APPROX_CHARS_PER_TOKEN,
    add_candidate,
    annotate_candidate,
    file_candidate,
    object_lookup,
    resolve_context_path,
)
from hydra_engine.knowledge.context_providers import DEFAULT_FAMILY_CANDIDATE_CAP, ProviderRequest, run_context_providers
from hydra_engine.objects.discovery import collect_hydra_objects
from hydra_engine.objects.registry import validate_object_registry_freshness
from hydra_engine.ports import clock as clock_port

DEFAULT_CONTEXT_BUDGET = 12000
EXPLICIT_OBJECT_PRIORITY = 0
EXPLICIT_PATH_PRIORITY = 5


def today() -> str:
    return clock_port.today()


def compile_context_packet(
    *,
    task: str,
    paths: ContextCompilerPaths,
    resolver_paths: ObjectLocations,
    surface_totals: dict[str, int],
    surface_file_count: int,
    provider: str = "",
    model: str = "",
    budget: int = DEFAULT_CONTEXT_BUDGET,
    node_values: list[str] | None = None,
    space: str = "",
    object_refs: list[str] | None = None,
    path_refs: list[str] | None = None,
    route_values: list[str] | None = None,
    view_values: list[str] | None = None,
    chars_per_token: int = APPROX_CHARS_PER_TOKEN,
    family_cap: int = DEFAULT_FAMILY_CANDIDATE_CAP,
    include_families: list[str] | None = None,
    exclude_families: list[str] | None = None,
    command_ids: tuple[str, ...] = (),
) -> dict:
    objects, object_errors = collect_hydra_objects(resolver_paths)
    by_ref = object_lookup(objects)
    by_path = {obj["path"]: obj for obj in objects}

    candidates: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    for raw in object_refs or []:
        obj = by_ref.get(raw.lower())
        if not obj:
            warnings.append(f"Object reference not found: {raw}")
            continue
        path = resolve_context_path(obj["path"], paths)
        if not path.exists():
            warnings.append(f"Resolved object path does not exist: {obj['path']}")
            continue
        add_candidate(
            candidates,
            seen,
            file_candidate(
                path,
                kind="object",
                reason=f"explicit object {raw}",
                priority=EXPLICIT_OBJECT_PRIORITY,
                paths=paths,
                source=obj["id"],
                chars_per_token=chars_per_token,
            ),
        )

    for raw in path_refs or []:
        path = resolve_context_path(raw, paths)
        if not path.exists() or not path.is_file():
            warnings.append(f"Path not found or not a file: {raw}")
            continue
        add_candidate(
            candidates,
            seen,
            file_candidate(
                path,
                kind="path",
                reason=f"explicit path {raw}",
                priority=EXPLICIT_PATH_PRIORITY,
                paths=paths,
                chars_per_token=chars_per_token,
            ),
        )

    object_seed_ids = frozenset(ref.lower() for ref in (object_refs or []))
    provider_request = ProviderRequest(
        task=task,
        paths=paths,
        resolver_paths=resolver_paths,
        object_seed_ids=object_seed_ids,
        chars_per_token=chars_per_token,
        family_cap=family_cap,
        node_values=tuple(node_values or []),
        space=space,
        route_values=tuple(route_values or []),
        path_values=tuple(path_refs or []),
        view_values=tuple(view_values or []),
        command_ids=command_ids,
    )
    provider_output = run_context_providers(
        provider_request,
        include_families=tuple(include_families or []),
        exclude_families=tuple(exclude_families or []),
    )
    for candidate in provider_output.candidates:
        add_candidate(candidates, seen, candidate)
    nodes_out = provider_output.nodes
    avoid_by_default = provider_output.avoid_by_default
    verify_commands = provider_output.verify
    warnings.extend(provider_output.warnings)

    required = [c for c in candidates if c.get("required")]
    optional = [c for c in candidates if not c.get("required")]

    selected: list[dict] = []
    omitted: list[dict] = []
    selected_tokens = 0
    # `rank` is a tiebreaker after priority: it is
    # `0` for every candidate not sourced from the shared search index, so
    # ordering among explicit/package/unit candidates is unchanged from
    # before context providers existed -- only search-provider candidates
    # sharing `PROVIDER_CANDIDATE_PRIORITY` are actually reordered by it.
    def _sort_key(item: dict) -> tuple:
        return (int(item["priority"]), item.get("rank", 0), item["path"])

    for candidate in sorted(required, key=_sort_key):
        selected.append(annotate_candidate(candidate, by_path))
        selected_tokens += int(candidate["approx_tokens"])
    required_tokens = selected_tokens
    # Never a hard failure: a required unit larger than the whole budget is
    # still included, and `required_overage` is the reported number that
    # makes the overrun visible instead of silently blowing the budget.
    required_overage = max(0, required_tokens - budget) if budget > 0 else 0

    for candidate in sorted(optional, key=_sort_key):
        tokens = int(candidate["approx_tokens"])
        if budget > 0 and selected_tokens + tokens <= budget:
            selected.append(annotate_candidate(candidate, by_path))
            selected_tokens += tokens
        else:
            omitted_candidate = {
                "path": candidate["path"],
                "kind": candidate["kind"],
                "reason": "token budget" if budget > 0 else "zero token budget",
                "approx_tokens": tokens,
            }
            if candidate.get("source"):
                omitted_candidate["source"] = candidate["source"]
            if candidate.get("stale_sources"):
                omitted_candidate["stale_sources"] = candidate["stale_sources"]
            omitted.append(omitted_candidate)

    # Rendered to text immediately: `validate_object_registry_freshness` now
    # returns `Finding`, and this packet's `--json` path
    # feeds `registry_freshness_errors` straight into `json.dumps`, which a
    # `Finding` dataclass cannot satisfy the way a plain string can.
    freshness_errors = [str(finding) for finding in validate_object_registry_freshness(resolver_paths)]
    return {
        "schema": "hydra-framework.context-packet.v2",
        "date": today(),
        "generated_at": clock_port.now_utc_iso(),
        "task": task,
        "provider": provider or "unspecified",
        "model": model or "unspecified",
        "budget_tokens": budget,
        "nodes": nodes_out,
        "views": provider_output.views,
        "effective_policy": provider_output.effective_policy,
        "route_expansions": provider_output.route_expansions,
        "selected_context": selected,
        "omitted_candidates": omitted,
        "required_units": [
            {"hydra_id": c.get("source", ""), "path": c["path"], "approx_tokens": c["approx_tokens"]}
            for c in required
        ],
        "avoid_by_default": avoid_by_default,
        "verify": verify_commands,
        "token_estimate": {
            "always_loaded_surfaces": surface_totals["approx_tokens"],
            "selected_context": selected_tokens,
            "total_if_loaded": surface_totals["approx_tokens"] + selected_tokens,
            "required_units": required_tokens,
            "required_overage": required_overage,
            "approximation": f"1 token ~= {chars_per_token} characters",
        },
        "provenance_freshness": {
            "resolver_objects": len(objects),
            "object_errors": object_errors,
            "registry_freshness_errors": freshness_errors,
        },
        "validation_reminders": [
            "Run `python3 .hydra-framework/scripts/hydra.py ref check` after object metadata changes.",
            "Run `python3 .hydra-framework/scripts/hydra.py validate` before finishing Hydra framework changes.",
        ],
        "known_risk_reminders": [
            "Treat provisional prompt routing as revisable when verified path bindings become available.",
        ],
        "warnings": warnings,
        "surface_file_count": surface_file_count,
    }
