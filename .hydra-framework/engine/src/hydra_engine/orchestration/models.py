"""Data contracts and validation primitives for orchestration state."""

from __future__ import annotations

import json
import re
from typing import Any

LEDGER_SCHEMA = "hydra-framework.orchestration-ledger.v1"

RUN_STATUSES = ("active", "completed", "failed", "handed_off", "recovery_required")
WORKER_STATUSES = (
    "queued", "acknowledged", "running", "waiting", "completed", "failed",
    "handed_off", "recovery_required", "cancelled",
)
REQUEST_KINDS = ("spawn", "message", "collect")
REQUEST_STATUSES = ("queued", "acknowledged", "rejected")
REVIEW_STATUSES = ("not_requested", "requested", "approved", "changes_requested", "rejected")
VALIDATION_STATUSES = ("not_run", "running", "passed", "partial", "failed")

_RUN_TRANSITIONS = {
    "active": frozenset({"completed", "failed", "handed_off", "recovery_required"}),
    "failed": frozenset({"recovery_required"}),
    "handed_off": frozenset({"active", "recovery_required"}),
    "recovery_required": frozenset({"active", "failed", "handed_off"}),
    "completed": frozenset(),
}
_WORKER_TRANSITIONS = {
    "queued": frozenset({"acknowledged", "running", "waiting", "completed", "failed", "handed_off", "recovery_required", "cancelled"}),
    "acknowledged": frozenset({"running", "waiting", "completed", "failed", "handed_off", "recovery_required", "cancelled"}),
    "running": frozenset({"waiting", "completed", "failed", "handed_off", "recovery_required", "cancelled"}),
    "waiting": frozenset({"running", "completed", "failed", "handed_off", "recovery_required", "cancelled"}),
    "failed": frozenset({"recovery_required"}),
    "handed_off": frozenset({"queued", "recovery_required"}),
    "recovery_required": frozenset({"queued", "failed", "handed_off", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}
_REVIEW_TRANSITIONS = {
    "not_requested": frozenset({"requested"}),
    "requested": frozenset({"approved", "changes_requested", "rejected"}),
    "changes_requested": frozenset({"requested", "approved", "rejected"}),
    "approved": frozenset({"requested", "rejected"}),
    "rejected": frozenset({"requested"}),
}
_VALIDATION_TRANSITIONS = {
    "not_run": frozenset({"running"}),
    "running": frozenset({"passed", "partial", "failed"}),
    "partial": frozenset({"running", "passed", "failed"}),
    "failed": frozenset({"running", "partial", "passed"}),
    "passed": frozenset({"running", "failed"}),
}

active_worker_statuses = frozenset({"queued", "acknowledged", "running", "waiting", "recovery_required"})
terminal_worker_statuses = frozenset({"completed", "failed", "cancelled"})
payload_limit_bytes = 8192
text_limit_bytes = 512
evidence_limit_bytes = 4096
max_evidence_items = 16
max_records = 2048
max_events = 4096
ledger_limit_bytes = 1_048_576
task_reference_limit_bytes = 512


class OrchestrationError(ValueError):
    """Base error for rejected control-plane operations."""


class LedgerError(OrchestrationError):
    """The local ledger cannot safely be read or updated."""


class LedgerCorruptError(LedgerError):
    """The local ledger is malformed; callers must not repair it implicitly."""


class NotFoundError(OrchestrationError):
    """A requested run, worker, request, or result does not exist."""


class OwnershipError(OrchestrationError):
    """An operation did not name an authorized current owner."""


class PolicyError(OrchestrationError):
    """A delegation policy or lifecycle constraint rejected an operation."""


class TransitionError(OrchestrationError):
    """A requested lifecycle transition is not allowed."""


class PayloadError(OrchestrationError):
    """A control-plane payload is absent, non-JSON, or too large."""


def bounded_text(value: object, label: str, limit: int = text_limit_bytes) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrchestrationError(f"{label} must be a non-empty string")
    result = value.strip()
    if len(result.encode("utf-8")) > limit:
        raise OrchestrationError(f"{label} exceeds the {limit}-byte limit")
    return result


def owner_name(value: object) -> str:
    result = bounded_text(value, "owner")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", result):
        raise OwnershipError("owner must be a simple explicit slug")
    return result


def identifier(value: object, label: str) -> str:
    result = bounded_text(value, label)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}", result):
        raise OrchestrationError(f"{label} has invalid characters")
    return result


def task_reference(value: object) -> str:
    """Validate a repository-relative task-record reference.

    A task reference is a path-like identity, not a copied task record. The
    traversal and absolute-path checks keep a corrupt ledger from turning a
    later existence check into an arbitrary filesystem read.
    """
    result = bounded_text(value, "task_id", task_reference_limit_bytes)
    parts = result.replace("\\", "/").split("/")
    if result.startswith("/") or ".." in parts or "\n" in result or "\r" in result:
        raise OrchestrationError("task_id must be a repository-relative reference")
    return result


def bounded_payload(value: object, label: str = "payload", limit: int = payload_limit_bytes) -> Any:
    if not isinstance(value, (dict, list)):
        raise PayloadError(f"{label} must be a structured JSON object or array")
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        normalized = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise PayloadError(f"{label} must be JSON-compatible") from error
    if len(encoded.encode("utf-8")) > limit:
        raise PayloadError(f"{label} exceeds the {limit}-byte limit")
    return normalized


def bounded_evidence(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise PayloadError("validation evidence must be a list of strings")
    if len(value) > max_evidence_items:
        raise PayloadError(f"validation evidence has more than {max_evidence_items} items")
    evidence = [bounded_text(item, "validation evidence item", text_limit_bytes) for item in value]
    bounded_payload(evidence, "validation evidence", evidence_limit_bytes)
    return evidence


def transition(current: str, target: str, transitions: dict[str, frozenset[str]], label: str) -> None:
    if target not in transitions:
        raise TransitionError(f"unknown {label} status `{target}`")
    if current == target:
        return
    if target not in transitions.get(current, frozenset()):
        raise TransitionError(f"cannot transition {label} from `{current}` to `{target}`")


def transition_run(current: str, target: str) -> None:
    transition(current, target, _RUN_TRANSITIONS, "run")


def transition_worker(current: str, target: str) -> None:
    transition(current, target, _WORKER_TRANSITIONS, "worker")


def transition_review(current: str, target: str) -> None:
    transition(current, target, _REVIEW_TRANSITIONS, "review")


def transition_validation(current: str, target: str) -> None:
    transition(current, target, _VALIDATION_TRANSITIONS, "validation")


def empty_ledger() -> dict[str, Any]:
    return {"schema": LEDGER_SCHEMA, "runs": {}, "workers": {}, "requests": {}, "messages": {}, "results": {}, "events": []}


def run_record(run_id: str, task_id: str, owner: str, now: str) -> dict[str, Any]:
    identifier(run_id, "run_id")
    task_reference(task_id)
    owner_name(owner)
    return {
        "run_id": run_id, "task_id": task_id, "owner": owner, "status": "active",
        "created_at": now, "updated_at": now, "worker_ids": [],
        "review_status": "not_requested", "validation_status": "not_run",
        "reviewer": "", "review_note": "", "validator": "", "validation_evidence": [],
    }


def worker_record(
    worker_id: str, request_id: str, run_id: str, task_id: str, owner: str,
    parent_worker_id: str, depth: int, role: str, task: str, reason: str,
    requested_class: str, capability_class: str, requested_effort: str,
    effort: str, provider: str, now: str,
) -> dict[str, Any]:
    identifier(worker_id, "worker_id")
    identifier(request_id, "request_id")
    identifier(run_id, "run_id")
    task_reference(task_id)
    owner_name(owner)
    if parent_worker_id:
        identifier(parent_worker_id, "parent_worker_id")
    bounded_text(role, "role")
    bounded_text(task, "worker task")
    bounded_text(reason, "delegation reason")
    bounded_text(requested_class, "requested capability class")
    bounded_text(capability_class, "capability class")
    bounded_text(requested_effort, "requested effort")
    bounded_text(effort, "effort")
    bounded_text(provider, "provider")
    return {
        "worker_id": worker_id, "request_id": request_id, "run_id": run_id,
        "task_id": task_id, "owner": owner, "parent_worker_id": parent_worker_id,
        "depth": depth, "role": role, "task": task, "reason": reason,
        "requested_capability_class": requested_class, "capability_class": capability_class,
        "requested_effort": requested_effort, "effort": effort, "provider": provider,
        "provider_ref": "", "status": "queued", "created_at": now, "updated_at": now,
        "last_error": "", "review_status": "not_requested", "validation_status": "not_run",
        "reviewer": "", "review_note": "", "validator": "", "validation_evidence": [],
    }


def request_record(
    request_id: str, kind: str, run_id: str, task_id: str, worker_id: str,
    owner: str, provider: str, now: str,
) -> dict[str, Any]:
    identifier(request_id, "request_id")
    bounded_text(kind, "request kind")
    identifier(run_id, "run_id")
    task_reference(task_id)
    identifier(worker_id, "worker_id")
    owner_name(owner)
    bounded_text(provider, "provider")
    return {
        "request_id": request_id, "kind": kind, "run_id": run_id, "task_id": task_id,
        "worker_id": worker_id, "owner": owner, "status": "queued", "provider": provider,
        "provider_ref": "", "created_at": now, "updated_at": now, "last_error": "",
    }


def message_record(
    message_id: str, request_id: str, run_id: str, task_id: str, worker_id: str,
    sender_owner: str, payload: Any, provider: str, now: str,
) -> dict[str, Any]:
    identifier(message_id, "message_id")
    identifier(request_id, "request_id")
    identifier(run_id, "run_id")
    task_reference(task_id)
    identifier(worker_id, "worker_id")
    owner_name(sender_owner)
    bounded_text(provider, "provider")
    bounded_payload(payload, "message payload")
    return {
        "message_id": message_id, "request_id": request_id, "run_id": run_id,
        "task_id": task_id, "worker_id": worker_id, "sender_owner": sender_owner,
        "payload": payload, "provider": provider, "provider_ref": "", "status": "queued",
        "created_at": now, "updated_at": now, "last_error": "",
    }


def result_record(
    result_id: str, request_id: str, run_id: str, task_id: str, worker_id: str,
    collector: str, payload: Any, complete: bool, now: str,
) -> dict[str, Any]:
    identifier(result_id, "result_id")
    identifier(request_id, "request_id")
    identifier(run_id, "run_id")
    task_reference(task_id)
    identifier(worker_id, "worker_id")
    owner_name(collector)
    bounded_payload(payload, "result payload")
    return {
        "result_id": result_id, "request_id": request_id, "run_id": run_id,
        "task_id": task_id, "worker_id": worker_id, "collector": collector,
        "payload": payload, "complete": complete, "status": "collected",
        "created_at": now, "updated_at": now,
    }


def event_record(event_id: str, kind: str, run_id: str, worker_id: str, actor: str, detail: str, now: str) -> dict[str, Any]:
    return {
        "event_id": event_id, "kind": kind, "run_id": run_id, "worker_id": worker_id,
        "actor": actor, "detail": bounded_text(detail, "event detail", text_limit_bytes), "at": now,
    }
