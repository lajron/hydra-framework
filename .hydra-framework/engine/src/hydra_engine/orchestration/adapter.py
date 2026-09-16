"""Provider-adapter boundary for orchestration requests.

The default adapter only records a local queue. A real provider integration
can implement the small ``submit`` protocol without changing control-plane
identity, policy, or lifecycle rules.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Protocol

from hydra_engine.orchestration import models


class AdapterError(models.OrchestrationError):
    """An adapter returned an invalid result or cannot be called safely."""


@dataclasses.dataclass(frozen=True)
class AdapterRequest:
    request_id: str
    kind: str
    run_id: str
    task_id: str
    worker_id: str
    owner: str
    payload: Any

    def __post_init__(self) -> None:
        models.identifier(self.request_id, "request_id")
        if self.kind not in models.REQUEST_KINDS:
            raise AdapterError(f"unsupported adapter request kind `{self.kind}`")
        models.identifier(self.run_id, "run_id")
        models.task_reference(self.task_id)
        models.identifier(self.worker_id, "worker_id")
        models.owner_name(self.owner)
        models.bounded_payload(self.payload, "adapter request payload")


@dataclasses.dataclass(frozen=True)
class AdapterReceipt:
    status: str
    provider: str
    provider_ref: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        if self.status not in models.REQUEST_STATUSES:
            raise AdapterError(f"adapter returned unknown status `{self.status}`")
        models.bounded_text(self.provider, "adapter provider")
        if self.provider_ref:
            models.bounded_text(self.provider_ref, "provider reference")
        if self.detail:
            models.bounded_text(self.detail, "adapter detail", models.text_limit_bytes)

    def as_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "provider": self.provider,
            "provider_ref": self.provider_ref,
            "detail": self.detail,
        }

    @classmethod
    def queued(cls, provider: str, detail: str) -> "AdapterReceipt":
        return cls("queued", provider, detail=detail)


class ProviderAdapter(Protocol):
    """The only provider capability the control plane assumes.

    ``submit`` means the adapter accepted a bounded request for its own
    handling. It does not mean that a model or worker has started running.
    """

    name: str

    def submit(self, request: AdapterRequest) -> AdapterReceipt:
        """Queue or acknowledge one spawn, message, or collect request."""


class QueueOnlyAdapter:
    """Honest fallback when no provider runtime adapter is installed."""

    def __init__(self, provider: str = "unconfigured"):
        self.name = models.bounded_text(provider, "adapter provider")

    def submit(self, request: AdapterRequest) -> AdapterReceipt:
        return AdapterReceipt.queued(
            self.name,
            "request is durable in the local control-plane ledger; no provider runtime was invoked",
        )


def request_only(provider: str) -> ProviderAdapter:
    """Return the explicit request boundary for a named provider.

    This is deliberately not a Claude, Codex, or other SDK adapter. It lets
    the control plane preserve the provider name on a queued request while
    making the absence of runtime execution evidence explicit.
    """
    return QueueOnlyAdapter(provider)


def adapter_name(adapter: ProviderAdapter | None) -> str:
    if adapter is None:
        return "unconfigured"
    return models.bounded_text(getattr(adapter, "name", ""), "adapter name")


def submit(adapter: ProviderAdapter | None, request: AdapterRequest) -> AdapterReceipt:
    """Call an adapter and preserve a local queued truth on adapter failure."""
    chosen = adapter or QueueOnlyAdapter()
    try:
        receipt = chosen.submit(request)
    except Exception as error:
        detail = f"adapter submission failed; request remains local-only: {type(error).__name__}"
        return AdapterReceipt.queued(adapter_name(chosen), detail)
    if not isinstance(receipt, AdapterReceipt):
        raise AdapterError("provider adapter must return AdapterReceipt")
    return receipt
