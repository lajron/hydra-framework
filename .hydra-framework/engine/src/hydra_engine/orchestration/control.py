"""Provider-neutral orchestration control-plane operations.

This module owns coordination records and policy checks. It does not schedule
processes, invoke a provider SDK, infer stale ownership, or reap workers.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from hydra_engine import config
from hydra_engine.orchestration import adapter, ledger, lifecycle, models
from hydra_engine.ports import clock, uids

OrchestrationError = models.OrchestrationError


class OrchestrationControl(lifecycle.OrchestrationLifecycle):
    """Apply explicit orchestration commands to one local ledger."""

    def __init__(
        self,
        store: ledger.LocalLedger,
        policy: config.DelegationPolicy,
        task_exists: Callable[[str], bool] | None = None,
        adapter_factory: Callable[[str], adapter.ProviderAdapter] = adapter.request_only,
    ) -> None:
        self.store = store
        self.policy = policy
        self.task_exists = task_exists
        self.adapter_factory = adapter_factory

    def start_run(self, run_id: str, task_id: str, owner: str) -> dict[str, Any]:
        models.identifier(run_id, "run_id")
        models.task_reference(task_id)
        models.owner_name(owner)
        self._require_task(task_id)

        def change(data: dict[str, Any]) -> dict[str, Any]:
            self._ensure_new(data, run_id)
            now = clock.now_utc_iso()
            record = models.run_record(run_id, task_id, owner, now)
            data["runs"][run_id] = record
            self._event(data, "run-started", run_id, "", owner, "run created")
            return dict(record)

        return self.store.update(change)

    def spawn(
        self,
        run_id: str,
        request_id: str,
        worker_id: str,
        worker_owner: str,
        actor: str,
        parent_worker_id: str,
        role: str,
        task: str,
        reason: str,
        requested_class: str,
        requested_effort: str,
        provider: str,
        payload: Any,
    ) -> dict[str, Any]:
        models.identifier(run_id, "run_id")
        models.identifier(request_id, "request_id")
        models.identifier(worker_id, "worker_id")
        if parent_worker_id:
            models.identifier(parent_worker_id, "parent_worker_id")
        models.owner_name(worker_owner)
        models.owner_name(actor)
        models.bounded_text(role, "role")
        models.bounded_text(task, "worker task")
        models.bounded_text(reason, "delegation reason")
        models.bounded_text(provider, "provider")
        models.bounded_payload(payload, "spawn payload")
        if reason not in self.policy.allowed_reasons:
            raise models.PolicyError(f"delegation reason `{reason}` is not allowed")
        if not self.policy.enabled:
            raise models.PolicyError("delegation is disabled by policy")

        def change(data: dict[str, Any]) -> dict[str, Any]:
            run = self._run(data, run_id)
            self._require_task(run["task_id"])
            if run["status"] != "active":
                raise models.PolicyError(f"run `{run_id}` is not active")
            self._ensure_new(data, request_id, worker_id)
            parent = None
            if parent_worker_id:
                parent = self._worker(data, parent_worker_id)
                if parent["run_id"] != run_id:
                    raise models.OwnershipError("parent worker belongs to a different run")
                if parent["status"] not in {"queued", "acknowledged", "running", "waiting"}:
                    raise models.PolicyError("parent worker must be active before it can spawn a child")
                self._require_owner(actor, parent["owner"], "parent worker")
                depth = parent["depth"] + 1
            else:
                self._require_owner(actor, run["owner"], "run")
                depth = 0
            if depth > self.policy.max_depth:
                raise models.PolicyError(
                    f"delegation depth {depth} exceeds configured maximum {self.policy.max_depth}"
                )
            active = sum(
                self._worker(data, item)["status"] in models.active_worker_statuses
                for item in run["worker_ids"]
            )
            if active >= self.policy.max_active_workers:
                raise models.PolicyError(
                    f"active worker limit {self.policy.max_active_workers} has been reached"
                )

            capability_class = self._capability_class(role, requested_class)
            effort = self._effort(role, requested_effort)
            now = clock.now_utc_iso()
            request = models.request_record(
                request_id, "spawn", run_id, run["task_id"], worker_id, actor, provider, now
            )
            worker = models.worker_record(
                worker_id, request_id, run_id, run["task_id"], worker_owner,
                parent_worker_id, depth, role, task, reason, requested_class,
                capability_class, requested_effort, effort, provider, now,
            )
            receipt = self._submit(request, payload)
            self._apply_receipt(request, worker, receipt)
            data["requests"][request_id] = request
            data["workers"][worker_id] = worker
            run["worker_ids"].append(worker_id)
            run["updated_at"] = now
            self._event(data, "worker-spawn-requested", run_id, worker_id, actor, receipt.detail or receipt.status)
            return dict(worker)

        return self.store.update(change)

    def message(
        self,
        run_id: str,
        worker_id: str,
        request_id: str,
        message_id: str,
        actor: str,
        provider: str,
        payload: Any,
    ) -> dict[str, Any]:
        return self._request_with_message(run_id, worker_id, request_id, message_id, actor, provider, payload)

    def collect(
        self,
        run_id: str,
        worker_id: str,
        request_id: str,
        result_id: str,
        actor: str,
        provider: str,
        payload: Any,
        complete: bool,
    ) -> dict[str, Any]:
        models.identifier(run_id, "run_id")
        models.identifier(worker_id, "worker_id")
        models.identifier(request_id, "request_id")
        models.identifier(result_id, "result_id")
        models.owner_name(actor)
        models.bounded_text(provider, "provider")
        models.bounded_payload(payload, "result payload")
        if not isinstance(complete, bool):
            raise models.PolicyError("result completion must be boolean")

        def change(data: dict[str, Any]) -> dict[str, Any]:
            run, worker = self._authorized_worker(data, run_id, worker_id, actor)
            self._require_task(run["task_id"])
            if run["status"] != "active":
                raise models.PolicyError(f"run `{run_id}` is not active")
            self._ensure_new(data, request_id, result_id)
            now = clock.now_utc_iso()
            request = models.request_record(
                request_id, "collect", run_id, run["task_id"], worker_id, actor, provider, now
            )
            result = models.result_record(
                result_id, request_id, run_id, run["task_id"], worker_id, actor, payload, complete, now
            )
            receipt = self._submit(request, payload)
            request["status"] = receipt.status
            request["provider"] = receipt.provider
            request["provider_ref"] = receipt.provider_ref
            request["last_error"] = receipt.detail if receipt.status == "rejected" else ""
            data["requests"][request_id] = request
            data["results"][result_id] = result
            if worker["status"] in {"queued", "acknowledged", "running"}:
                models.transition_worker(worker["status"], "waiting")
                worker["status"] = "waiting"
            worker["updated_at"] = now
            run["updated_at"] = now
            detail = receipt.detail or "result supplied to the local ledger"
            self._event(data, "result-collected", run_id, worker_id, actor, detail)
            return dict(result)

        return self.store.update(change)

    def snapshot(self, run_id: str = "") -> dict[str, Any]:
        data = self.store.read()
        if not run_id:
            return data
        run = self._run(data, run_id)
        worker_ids = set(run["worker_ids"])
        return {
            "run": dict(run),
            "workers": [dict(data["workers"][item]) for item in run["worker_ids"]],
            "requests": [dict(item) for item in data["requests"].values() if item.get("run_id") == run_id],
            "messages": [dict(item) for item in data["messages"].values() if item.get("worker_id") in worker_ids],
            "results": [dict(item) for item in data["results"].values() if item.get("worker_id") in worker_ids],
            "events": [dict(item) for item in data["events"] if item.get("run_id") == run_id],
        }

    def _request_with_message(self, run_id, worker_id, request_id, message_id, actor, provider, payload):
        for value, label in ((run_id, "run_id"), (worker_id, "worker_id"), (request_id, "request_id"), (message_id, "message_id")):
            models.identifier(value, label)
        models.owner_name(actor)
        models.bounded_text(provider, "provider")
        models.bounded_payload(payload, "message payload")

        def change(data: dict[str, Any]) -> dict[str, Any]:
            run, worker = self._authorized_worker(data, run_id, worker_id, actor)
            self._require_task(run["task_id"])
            if run["status"] != "active":
                raise models.PolicyError(f"run `{run_id}` is not active")
            self._ensure_new(data, request_id, message_id)
            now = clock.now_utc_iso()
            request = models.request_record(
                request_id, "message", run_id, run["task_id"], worker_id, actor, provider, now
            )
            message = models.message_record(
                message_id, request_id, run_id, run["task_id"], worker_id, actor, payload, provider, now
            )
            receipt = self._submit(request, payload)
            request["status"] = receipt.status
            request["provider"] = receipt.provider
            request["provider_ref"] = receipt.provider_ref
            request["last_error"] = receipt.detail if receipt.status == "rejected" else ""
            message["status"] = receipt.status
            message["provider"] = receipt.provider
            message["provider_ref"] = receipt.provider_ref
            message["last_error"] = receipt.detail if receipt.status == "rejected" else ""
            data["requests"][request_id] = request
            data["messages"][message_id] = message
            run["updated_at"] = now
            worker["updated_at"] = now
            self._event(data, "message-requested", run_id, worker_id, actor, receipt.detail or receipt.status)
            return dict(message)

        return self.store.update(change)

    def _run(self, data, run_id: str) -> dict[str, Any]:
        try:
            return data["runs"][run_id]
        except KeyError as error:
            raise models.NotFoundError(f"run `{run_id}` was not found") from error

    def _worker(self, data, worker_id: str) -> dict[str, Any]:
        try:
            return data["workers"][worker_id]
        except KeyError as error:
            raise models.NotFoundError(f"worker `{worker_id}` was not found") from error

    def _ensure_new(self, data, *identities: str) -> None:
        for identity in identities:
            if any(identity in data[key] for key in ("runs", "workers", "requests", "messages", "results")):
                raise models.PolicyError(f"identity `{identity}` already exists")

    def _require_task(self, task_id: str) -> None:
        if self.task_exists is not None and not self.task_exists(task_id):
            raise models.PolicyError(f"task record reference is not available: {task_id}")

    @staticmethod
    def _require_owner(actor: str, expected: str, label: str) -> None:
        if actor != expected:
            raise models.OwnershipError(f"{label} is owned by `{expected}`, not `{actor}`")

    def _capability_class(self, role: str, requested: str) -> str:
        policy = config.role_policy(self.policy, role)
        return requested if requested in policy.allowed_capability_classes else policy.fallback_capability_class

    def _effort(self, role: str, requested: str) -> str:
        policy = config.role_policy(self.policy, role)
        if requested not in config.EFFORT_ORDER:
            raise models.PolicyError(f"effort `{requested}` is not supported")
        return min(requested, policy.effort_ceiling, key=config.EFFORT_ORDER.index)

    def _submit(self, request: dict[str, Any], payload: Any) -> adapter.AdapterReceipt:
        request_object = adapter.AdapterRequest(
            request_id=request["request_id"], kind=request["kind"], run_id=request["run_id"],
            task_id=request["task_id"], worker_id=request["worker_id"], owner=request["owner"],
            payload=payload,
        )
        return adapter.submit(self.adapter_factory(request["provider"]), request_object)

    @staticmethod
    def _apply_receipt(request, worker, receipt: adapter.AdapterReceipt) -> None:
        request["status"] = receipt.status
        request["provider"] = receipt.provider
        request["provider_ref"] = receipt.provider_ref
        request["last_error"] = receipt.detail if receipt.status == "rejected" else ""
        worker["provider"] = receipt.provider
        worker["provider_ref"] = receipt.provider_ref
        worker["status"] = "acknowledged" if receipt.status == "acknowledged" else "failed" if receipt.status == "rejected" else "queued"
        worker["last_error"] = receipt.detail if receipt.status == "rejected" else ""

    def _event(self, data, kind, run_id, worker_id, actor, detail) -> None:
        if len(data["events"]) >= models.max_events:
            raise models.PolicyError("orchestration event limit has been reached")
        data["events"].append(models.event_record(f"evt-{uids.new_uid()}", kind, run_id, worker_id, actor, detail, clock.now_utc_iso()))

def for_repository(
    root: Path,
    hydra: Path,
    local: Path,
    task_exists: Callable[[str], bool] | None = None,
) -> OrchestrationControl:
    """Build a control plane from shared policy and private ledger paths."""
    paths = ledger.OrchestrationPaths(root=root, hydra=hydra, local=local)
    effective = config.load_effective_config(config.ConfigPaths(root=root, hydra=hydra, local=local))
    return OrchestrationControl(ledger.LocalLedger(paths), effective.delegation, task_exists)
