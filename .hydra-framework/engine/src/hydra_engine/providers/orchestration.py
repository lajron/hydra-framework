"""Provider-map validation and rendering for orchestration request boundaries."""

from __future__ import annotations

from hydra_engine.finding import Finding

ORCHESTRATION_OPERATIONS = ("spawn", "message", "collect")
ORCHESTRATION_REQUEST_STATES = ("request-only", "unsupported")


def modes(mapping: dict) -> dict[str, str]:
    """Resolve request-boundary declarations without inventing support."""
    section = mapping.get("orchestration")
    if not isinstance(section, dict):
        return {operation: "unsupported" for operation in ORCHESTRATION_OPERATIONS}
    return {
        operation: state if state in ORCHESTRATION_REQUEST_STATES else "unsupported"
        for operation in ORCHESTRATION_OPERATIONS
        for state in [_text(section.get(operation))]
    }


def request_instruction(mapping: dict) -> str:
    """Render the explicit request boundary into a provider agent wrapper."""
    if not isinstance(mapping.get("orchestration"), dict):
        return ""
    resolved = modes(mapping)
    request_only = [item for item in ORCHESTRATION_OPERATIONS if resolved[item] == "request-only"]
    unsupported = [item for item in ORCHESTRATION_OPERATIONS if resolved[item] == "unsupported"]
    lines = [
        "\n## Orchestration Request Boundary\n",
        "This provider map describes an explicit request boundary for Hydra orchestration. "
        "It does not invoke a provider SDK or claim that the provider executed a request.",
    ]
    if request_only:
        lines.append(
            f"Request-only operations: {', '.join(request_only)}. The runtime may queue or "
            "acknowledge these requests; Hydra must not infer execution or completion from "
            "the request alone."
        )
    if unsupported:
        lines.append(f"Unsupported operations for this provider map: {', '.join(unsupported)}.")
    return "\n".join(lines) + "\n"


def validate_mapping(data: dict, label: str) -> list[Finding]:
    """Validate an optional provider orchestration section."""
    if "orchestration" not in data:
        return []
    section = data.get("orchestration")
    if not isinstance(section, dict):
        return [Finding(path=label, code="capability-maps", detail=f"{label} orchestration must be a YAML map")]
    findings = []
    for operation in ORCHESTRATION_OPERATIONS:
        state = _text(section.get(operation))
        if state not in ORCHESTRATION_REQUEST_STATES:
            findings.append(Finding(
                path=label,
                code="capability-maps",
                detail=f"{label} orchestration `{operation}` must be request-only or unsupported",
            ))
    return findings


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
