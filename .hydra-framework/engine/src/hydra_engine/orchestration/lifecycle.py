"""Lifecycle, ownership transfer, review, and validation operations."""

from __future__ import annotations

from typing import Any

from hydra_engine.orchestration import models


class OrchestrationLifecycle:
    """Mixin for lifecycle operations over an ``OrchestrationControl``."""

    def transition(self, kind: str, target_id: str, actor: str, status: str) -> dict[str, Any]:
        models.owner_name(actor)
        models.identifier(target_id, "target_id")

        def change(data: dict[str, Any]) -> dict[str, Any]:
            target, run_id, worker_id = self._target(data, kind, target_id)
            self._require_task(data["runs"][run_id]["task_id"])
            self._require_owner(actor, target["owner"], kind)
            if status == "handed_off":
                raise models.PolicyError("use explicit handoff for the handed_off state")
            if kind == "run":
                models.transition_run(target["status"], status)
                if status == "completed":
                    self._require_run_completion(data, target)
            else:
                models.transition_worker(target["status"], status)
                if status == "completed" and not self._has_complete_result(data, worker_id):
                    raise models.PolicyError("worker completion requires a collected complete result")
            now = self._now()
            target["status"] = status
            target["updated_at"] = now
            self._event(data, f"{kind}-transitioned", run_id, worker_id, actor, status)
            return dict(target)

        return self.store.update(change)

    def handoff(self, kind: str, target_id: str, actor: str, new_owner: str) -> dict[str, Any]:
        models.owner_name(actor)
        models.owner_name(new_owner)
        models.identifier(target_id, "target_id")
        if actor == new_owner:
            raise models.OwnershipError("handoff requires a different explicit owner")

        def change(data: dict[str, Any]) -> dict[str, Any]:
            target, run_id, worker_id = self._target(data, kind, target_id)
            self._require_task(data["runs"][run_id]["task_id"])
            self._require_owner(actor, target["owner"], kind)
            if kind == "run":
                models.transition_run(target["status"], "handed_off")
            else:
                models.transition_worker(target["status"], "handed_off")
            now = self._now()
            target["owner"] = new_owner
            target["status"] = "handed_off"
            target["updated_at"] = now
            self._event(data, f"{kind}-handed-off", run_id, worker_id, actor, f"owner={new_owner}")
            return dict(target)

        return self.store.update(change)

    def recover(self, kind: str, target_id: str, actor: str, from_owner: str) -> dict[str, Any]:
        models.owner_name(actor)
        models.owner_name(from_owner)
        models.identifier(target_id, "target_id")
        if actor == from_owner:
            raise models.OwnershipError("recovery requires a different explicit owner")

        def change(data: dict[str, Any]) -> dict[str, Any]:
            target, run_id, worker_id = self._target(data, kind, target_id)
            if target["owner"] != from_owner:
                raise models.OwnershipError(
                    f"record owner is `{target['owner']}`, not the named recovery source `{from_owner}`"
                )
            if target["status"] not in {"handed_off", "recovery_required"}:
                raise models.PolicyError("recovery requires an explicit handoff or recovery_required state")
            self._require_task(data["runs"][run_id]["task_id"])
            next_status = "active" if kind == "run" else "queued"
            if kind == "run":
                models.transition_run(target["status"], next_status)
            else:
                models.transition_worker(target["status"], next_status)
            now = self._now()
            target["owner"] = actor
            target["status"] = next_status
            target["updated_at"] = now
            self._event(data, f"{kind}-recovered", run_id, worker_id, actor, f"from_owner={from_owner}")
            return dict(target)

        return self.store.update(change)

    def review(self, kind: str, target_id: str, actor: str, status: str, note: str) -> dict[str, Any]:
        models.owner_name(actor)
        models.identifier(target_id, "target_id")
        if note:
            models.bounded_text(note, "review note")

        def change(data: dict[str, Any]) -> dict[str, Any]:
            target, run_id, worker_id = self._target(data, kind, target_id)
            owner = target["owner"]
            if status == "requested":
                self._require_owner(actor, owner, kind)
            else:
                if actor == owner:
                    raise models.OwnershipError("review decisions require an independent explicit reviewer")
                if not self._reviewable(data, kind, run_id, worker_id):
                    raise models.PolicyError("review requires a collected complete result")
            models.transition_review(target["review_status"], status)
            now = self._now()
            target["review_status"] = status
            target["reviewer"] = actor if status != "requested" else ""
            target["review_note"] = note
            target["updated_at"] = now
            self._event(data, f"{kind}-reviewed", run_id, worker_id, actor, status)
            return dict(target)

        return self.store.update(change)

    def validate(self, kind: str, target_id: str, actor: str, status: str, evidence: list[str]) -> dict[str, Any]:
        models.owner_name(actor)
        models.identifier(target_id, "target_id")
        evidence = models.bounded_evidence(evidence)

        def change(data: dict[str, Any]) -> dict[str, Any]:
            target, run_id, worker_id = self._target(data, kind, target_id)
            owner = target["owner"]
            if status == "running":
                self._require_owner(actor, owner, kind)
            else:
                if actor == owner:
                    raise models.OwnershipError("validation decisions require an independent explicit validator")
                if not evidence:
                    raise models.PolicyError("a terminal validation state requires evidence")
                if not self._reviewable(data, kind, run_id, worker_id):
                    raise models.PolicyError("validation requires a collected complete result")
            models.transition_validation(target["validation_status"], status)
            now = self._now()
            target["validation_status"] = status
            target["validator"] = actor if status != "running" else ""
            target["validation_evidence"] = evidence
            target["updated_at"] = now
            self._event(data, f"{kind}-validated", run_id, worker_id, actor, status)
            return dict(target)

        return self.store.update(change)

    def _target(self, data, kind: str, target_id: str):
        if kind == "run":
            return self._run(data, target_id), target_id, ""
        if kind == "worker":
            worker = self._worker(data, target_id)
            return worker, worker["run_id"], target_id
        raise models.PolicyError("target kind must be `run` or `worker`")

    def _authorized_worker(self, data, run_id: str, worker_id: str, actor: str):
        run = self._run(data, run_id)
        worker = self._worker(data, worker_id)
        if worker["run_id"] != run_id:
            raise models.NotFoundError(f"worker `{worker_id}` is not part of run `{run_id}`")
        if actor == run["owner"]:
            return run, worker
        self._require_owner(actor, worker["owner"], "run or worker")
        return run, worker

    def _has_complete_result(self, data, worker_id: str) -> bool:
        return any(
            item.get("worker_id") == worker_id and item.get("complete") is True
            for item in data["results"].values()
        )

    def _reviewable(self, data, kind: str, run_id: str, worker_id: str) -> bool:
        if kind == "worker":
            return self._has_complete_result(data, worker_id)
        workers = data["runs"][run_id]["worker_ids"]
        return all(self._has_complete_result(data, item) for item in workers)

    def _require_run_completion(self, data, run) -> None:
        if any(
            data["workers"][item]["status"] not in models.terminal_worker_statuses
            for item in run["worker_ids"]
        ):
            raise models.PolicyError("run completion requires every worker to be terminal")
        if run["review_status"] != "approved" or run["validation_status"] != "passed":
            raise models.PolicyError("run completion requires approved review and passed validation")

    @staticmethod
    def _now() -> str:
        from hydra_engine.ports import clock

        return clock.now_utc_iso()
