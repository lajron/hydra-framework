"""Validation for the persisted orchestration ledger schema."""

from __future__ import annotations

from hydra_engine.orchestration import models


def _corrupt(detail: str) -> models.LedgerCorruptError:
    return models.LedgerCorruptError(f"local orchestration ledger is corrupt: {detail}")


def validate_ledger(data: object) -> None:
    if not isinstance(data, dict):
        raise _corrupt("top-level value must be an object")
    expected = {"schema", "runs", "workers", "requests", "messages", "results", "events"}
    if set(data) != expected:
        raise _corrupt("top-level keys do not match the v1 schema")
    if data.get("schema") != models.LEDGER_SCHEMA:
        raise _corrupt("schema is not supported")
    for key in ("runs", "workers", "requests", "messages", "results"):
        if not isinstance(data[key], dict) or len(data[key]) > models.max_records:
            raise _corrupt(f"{key} must be a bounded object")
    if not isinstance(data["events"], list) or len(data["events"]) > models.max_events:
        raise _corrupt("events must be a bounded list")

    runs = data["runs"]
    for key, record in runs.items():
        _record_text(record, key, "run_id", "task_id", "owner", "created_at", "updated_at")
        _key_matches(record, key, "run_id")
        try:
            models.identifier(record["run_id"], "run_id")
            models.task_reference(record["task_id"])
            models.owner_name(record["owner"])
        except models.OrchestrationError as error:
            raise _corrupt(f"run `{key}` has invalid identity") from error
        if record["status"] not in models.RUN_STATUSES:
            raise _corrupt(f"run `{key}` has an unknown status")
        if not isinstance(record.get("worker_ids"), list) or len(record["worker_ids"]) > models.max_records:
            raise _corrupt(f"run `{key}` has invalid worker_ids")
        if any(not isinstance(item, str) for item in record["worker_ids"]):
            raise _corrupt(f"run `{key}` has non-string worker_ids")
        if len(set(record["worker_ids"])) != len(record["worker_ids"]):
            raise _corrupt(f"run `{key}` has duplicate worker_ids")
        if record.get("review_status") not in models.REVIEW_STATUSES or record.get("validation_status") not in models.VALIDATION_STATUSES:
            raise _corrupt(f"run `{key}` has invalid review or validation state")
        try:
            models.bounded_evidence(record.get("validation_evidence"))
        except models.OrchestrationError as error:
            raise _corrupt(f"run `{key}` has invalid validation evidence") from error

    workers = data["workers"]
    for key, record in workers.items():
        _record_text(record, key, "worker_id", "request_id", "run_id", "task_id", "owner", "role", "task", "reason", "created_at", "updated_at")
        _key_matches(record, key, "worker_id")
        if record["status"] not in models.WORKER_STATUSES or not isinstance(record.get("depth"), int) or isinstance(record["depth"], bool) or record["depth"] < 0:
            raise _corrupt(f"worker `{key}` has invalid identity or status")
        try:
            models.identifier(record["worker_id"], "worker_id")
            models.identifier(record["request_id"], "request_id")
            models.identifier(record["run_id"], "run_id")
            models.task_reference(record["task_id"])
            models.owner_name(record["owner"])
            for field in ("role", "task", "reason", "requested_capability_class", "capability_class", "requested_effort", "effort", "provider"):
                models.bounded_text(record.get(field), field)
        except models.OrchestrationError as error:
            raise _corrupt(f"worker `{key}` has invalid fields") from error
        if record.get("review_status") not in models.REVIEW_STATUSES or record.get("validation_status") not in models.VALIDATION_STATUSES:
            raise _corrupt(f"worker `{key}` has invalid review or validation state")
        try:
            models.bounded_evidence(record.get("validation_evidence"))
        except models.OrchestrationError as error:
            raise _corrupt(f"worker `{key}` has invalid validation evidence") from error
        if record["run_id"] not in runs or record["request_id"] not in data["requests"]:
            raise _corrupt(f"worker `{key}` has a dangling run or request reference")
        parent = record.get("parent_worker_id", "")
        if not isinstance(parent, str):
            raise _corrupt(f"worker `{key}` has an invalid parent reference")
        if parent:
            try:
                models.identifier(parent, "parent_worker_id")
            except models.OrchestrationError as error:
                raise _corrupt(f"worker `{key}` has an invalid parent reference") from error
        if parent and (parent not in workers or workers[parent]["run_id"] != record["run_id"]):
            raise _corrupt(f"worker `{key}` has a dangling parent reference")

    requests = data["requests"]
    for key, record in requests.items():
        _record_text(record, key, "request_id", "kind", "run_id", "task_id", "worker_id", "owner", "provider", "created_at", "updated_at")
        _key_matches(record, key, "request_id")
        if record["kind"] not in models.REQUEST_KINDS or record["status"] not in models.REQUEST_STATUSES or record["run_id"] not in runs:
            raise _corrupt(f"request `{key}` has invalid kind, status, or run")
        try:
            models.identifier(record["request_id"], "request_id")
            models.identifier(record["run_id"], "run_id")
            models.task_reference(record["task_id"])
            models.owner_name(record["owner"])
            models.bounded_text(record["provider"], "provider")
        except models.OrchestrationError as error:
            raise _corrupt(f"request `{key}` has invalid fields") from error
        if record.get("worker_id") and record["worker_id"] not in workers:
            raise _corrupt(f"request `{key}` has a dangling worker reference")

    for key, record in data["messages"].items():
        _record_text(record, key, "message_id", "request_id", "run_id", "task_id", "worker_id", "sender_owner", "provider", "created_at", "updated_at")
        _key_matches(record, key, "message_id")
        if record["status"] not in models.REQUEST_STATUSES or record["run_id"] not in runs or record["worker_id"] not in workers or record["request_id"] not in requests:
            raise _corrupt(f"message `{key}` has an invalid reference or status")
        if requests[record["request_id"]].get("kind") != "message":
            raise _corrupt(f"message `{key}` does not reference a message request")
        try:
            models.bounded_payload(record.get("payload"), "message payload")
        except models.OrchestrationError as error:
            raise _corrupt(f"message `{key}` payload is invalid") from error

    for key, record in data["results"].items():
        _record_text(record, key, "result_id", "request_id", "run_id", "task_id", "worker_id", "collector", "created_at", "updated_at")
        _key_matches(record, key, "result_id")
        if record["run_id"] not in runs or record["worker_id"] not in workers or record["request_id"] not in requests or not isinstance(record.get("complete"), bool):
            raise _corrupt(f"result `{key}` has an invalid reference")
        if requests[record["request_id"]].get("kind") != "collect":
            raise _corrupt(f"result `{key}` does not reference a collect request")
        try:
            models.bounded_payload(record.get("payload"), "result payload")
        except models.OrchestrationError as error:
            raise _corrupt(f"result `{key}` payload is invalid") from error

    event_ids: set[str] = set()
    for record in data["events"]:
        if not isinstance(record, dict):
            raise _corrupt("event must be an object")
        _record_text(record, record.get("event_id", ""), "event_id", "kind", "run_id", "actor", "detail", "at")
        if record["event_id"] in event_ids:
            raise _corrupt(f"event `{record['event_id']}` is duplicated")
        event_ids.add(record["event_id"])
        try:
            models.identifier(record["event_id"], "event_id")
            models.identifier(record["run_id"], "run_id")
            models.owner_name(record["actor"])
        except models.OrchestrationError as error:
            raise _corrupt("event has invalid identity") from error
        if record["run_id"] not in runs or (record.get("worker_id") and record["worker_id"] not in workers):
            raise _corrupt("event has a dangling reference")

    for run_id, run in runs.items():
        for worker_id in run["worker_ids"]:
            if worker_id not in workers or workers[worker_id]["run_id"] != run_id:
                raise _corrupt(f"run `{run_id}` has a dangling worker id")

    for worker_id, worker in workers.items():
        parent = worker.get("parent_worker_id", "")
        if parent:
            if workers[parent]["depth"] + 1 != worker["depth"]:
                raise _corrupt(f"worker `{worker_id}` has an inconsistent parent depth")
            seen: set[str] = set()
            current = parent
            while current:
                if current in seen or current == worker_id:
                    raise _corrupt(f"worker `{worker_id}` has a cyclic parent chain")
                seen.add(current)
                current = workers[current].get("parent_worker_id", "")

    _validate_relationships(data)


def _record_text(record: object, key: object, *fields: str) -> None:
    if not isinstance(record, dict):
        raise _corrupt(f"record `{key}` is not an object")
    for field in fields:
        if not isinstance(record.get(field), str) or not record[field]:
            raise _corrupt(f"record `{key}` is missing `{field}`")


def _key_matches(record: dict, key: object, field: str) -> None:
    if not isinstance(key, str) or record.get(field) != key:
        raise _corrupt(f"record key does not match `{field}`")


def _validate_relationships(data: dict) -> None:
    runs = data["runs"]
    workers = data["workers"]
    requests = data["requests"]
    for worker_id, worker in workers.items():
        run = runs[worker["run_id"]]
        request = requests[worker["request_id"]]
        if worker_id not in run["worker_ids"]:
            raise _corrupt(f"worker `{worker_id}` is not listed by its run")
        if worker["task_id"] != run["task_id"]:
            raise _corrupt(f"worker `{worker_id}` task does not match its run")
        if request["kind"] != "spawn" or request["worker_id"] != worker_id:
            raise _corrupt(f"worker `{worker_id}` does not match its spawn request")
        if request["run_id"] != worker["run_id"] or request["task_id"] != worker["task_id"]:
            raise _corrupt(f"worker `{worker_id}` request does not match its run")
    for request_id, request in requests.items():
        run = runs[request["run_id"]]
        if request["task_id"] != run["task_id"]:
            raise _corrupt(f"request `{request_id}` task does not match its run")
        worker_id = request.get("worker_id", "")
        if worker_id:
            worker = workers[worker_id]
            if worker["run_id"] != request["run_id"] or worker["task_id"] != request["task_id"]:
                raise _corrupt(f"request `{request_id}` does not match its worker")
    for collection in (data["messages"], data["results"]):
        for record in collection.values():
            worker = workers[record["worker_id"]]
            run = runs[record["run_id"]]
            request = requests[record["request_id"]]
            if worker["run_id"] != record["run_id"] or worker["task_id"] != record["task_id"]:
                raise _corrupt("worker record does not match its message or result")
            if run["task_id"] != record["task_id"] or request["run_id"] != record["run_id"] or request["task_id"] != record["task_id"]:
                raise _corrupt("request or run does not match its message or result")
