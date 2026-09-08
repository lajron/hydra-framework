"""Knowledge-view selection and composition for routing consumers."""

from __future__ import annotations

from hydra_engine.identity.slugs import slugify
from hydra_engine.knowledge.routing import context_terms
from hydra_engine.knowledge.views import ViewConflictError, compose_views, discover_views


def normalized_token(value: str) -> str:
    return slugify(value)


def select_and_compose_views(task: str, requested: tuple[str, ...], paths, bound_node_ids: set[str], warnings: list[str], *, views=None):
    views = discover_views(paths) if views is None else list(views)
    by_id = {view.hydra_id: view for view in views}
    by_slug = {view.view_id: view.hydra_id for view in views}
    if requested:
        selected: set[str] = set()
        for value in requested:
            normalized = value.lower()
            view_id = normalized if normalized.startswith("hydra://knowledge-view/") else by_slug.get(slugify(normalized), "")
            if view_id in by_id:
                selected.add(view_id)
            else:
                warnings.append(f"View not found: {value}")
    else:
        task_terms = context_terms(task)
        selected = {
            view.hydra_id for view in views
            if any(len(task_terms & context_terms(" ".join((route.name, *route.use_when)))) >= 2 for route in view.routes)
        }
    composed = compose_views(selected, by_id, bound_node_ids=bound_node_ids) if selected else None
    return selected, composed


__all__ = ("ViewConflictError", "normalized_token", "select_and_compose_views")
