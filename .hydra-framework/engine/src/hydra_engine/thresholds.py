"""Registry for governed numeric thresholds in the Hydra engine.

The registry is intentionally pure data. Runtime modules own their constants;
tests compare those constants against the exact values below and fail when a
public integer threshold is added without classification.
"""

from __future__ import annotations

from dataclasses import dataclass

TEAM_TUNABLE_POLICY = "team-tunable-policy"
ENGINE_INVARIANT = "engine-invariant"


@dataclass(frozen=True)
class Threshold:
    module: str
    name: str
    value: int
    classification: str
    reason: str

    @property
    def key(self) -> str:
        return f"{self.module}.{self.name}"


THRESHOLDS: tuple[Threshold, ...] = (
    Threshold("hydra_engine.agent_hooks.logs", "LOG_CONTEXT_AFTER_LINES", 2, ENGINE_INVARIANT, "log excerpt context heuristic"),
    Threshold("hydra_engine.agent_hooks.logs", "LOG_CONTEXT_BEFORE_LINES", 2, ENGINE_INVARIANT, "log excerpt context heuristic"),
    Threshold("hydra_engine.agent_hooks.retry_state", "RETRY_FINGERPRINT_SAMPLE_CHARS", 4000, ENGINE_INVARIANT, "retry fingerprint material"),
    Threshold("hydra_engine.agent_hooks.retry_state", "RETRY_FINGERPRINT_STORED_SAMPLE_CHARS", 3500, ENGINE_INVARIANT, "keeps one retry-state JSONL append under a single page write"),
    Threshold("hydra_engine.agent_hooks.retry_state", "RETRY_FINGERPRINT_SUMMARY_LINES", 24, ENGINE_INVARIANT, "retry fingerprint material"),
    Threshold("hydra_engine.agent_hooks.retry_state", "RETRY_STATE_GROWTH_ADVISORY_LINES", 5000, TEAM_TUNABLE_POLICY, "append-only retry-state log readability backstop"),
    Threshold("hydra_engine.agent_hooks.subagent_context", "SUBAGENT_CONTEXT_MAX_PACKAGES_NAMED", 6, ENGINE_INVARIANT, "bounded subagent hook context"),
    Threshold("hydra_engine.agent_hooks.subagent_context", "SUBAGENT_CONTEXT_TOKEN_BUDGET", 350, TEAM_TUNABLE_POLICY, "subagent hook context budget"),
    Threshold("hydra_engine.agent_hooks.token_budget", "LARGE_LOG_CHARS_DEFAULT", 20000, TEAM_TUNABLE_POLICY, "token-hook large-output policy default"),
    Threshold("hydra_engine.agent_hooks.token_budget", "LARGE_LOG_LINES_DEFAULT", 120, TEAM_TUNABLE_POLICY, "token-hook large-output policy default"),
    Threshold("hydra_engine.agent_hooks.token_budget", "RETRY_MAX_ATTEMPTS_DEFAULT", 2, TEAM_TUNABLE_POLICY, "token-hook retry policy default"),
    Threshold("hydra_engine.agent_hooks.token_budget", "SUMMARY_MAX_LINES_DEFAULT", 80, TEAM_TUNABLE_POLICY, "token-hook summary policy default"),
    Threshold("hydra_engine.architecture", "HIGH_IN_DEGREE_MAX_LINES", 150, ENGINE_INVARIANT, "Hydra engine architecture boundary"),
    Threshold("hydra_engine.architecture", "HIGH_IN_DEGREE_THRESHOLD", 10, ENGINE_INVARIANT, "Hydra engine architecture boundary"),
    Threshold("hydra_engine.architecture", "MAX_COMPOSITION_ROOT_LINES", 200, ENGINE_INVARIANT, "Hydra engine architecture boundary"),
    Threshold("hydra_engine.architecture", "MAX_FAN_OUT", 8, ENGINE_INVARIANT, "Hydra engine architecture boundary"),
    Threshold("hydra_engine.architecture", "MAX_SOURCE_LINES", 400, ENGINE_INVARIANT, "Hydra engine architecture boundary"),
    Threshold("hydra_engine.architecture", "MAX_TEST_LINES", 600, ENGINE_INVARIANT, "Hydra engine architecture boundary"),
    Threshold("hydra_engine.cli.route_prompt", "ROUTE_PROMPT_REEMIT_EVERY", 25, ENGINE_INVARIANT, "route-prompt session suppression safety interval"),
    Threshold("hydra_engine.commands.agent_hooks", "RETRY_FINGERPRINT_DISPLAY_CHARS", 12, ENGINE_INVARIANT, "bounded CLI display"),
    Threshold("hydra_engine.commands.agent_hooks", "TOKEN_BUDGET_EXCEEDED_REPORT_LIMIT", 5, ENGINE_INVARIANT, "bounded CLI display"),
    Threshold("hydra_engine.commands.hooks", "PACKAGE_GATE_REPORT_LIMIT", 8, ENGINE_INVARIANT, "bounded hook output"),
    Threshold("hydra_engine.commands.installation", "ADOPT_HOST_SIGNAL_REPORT_LIMIT", 4, ENGINE_INVARIANT, "bounded CLI display"),
    Threshold("hydra_engine.commands.installation", "INIT_CONFLICT_REPORT_LIMIT", 10, ENGINE_INVARIANT, "bounded CLI display"),
    Threshold("hydra_engine.commands.installation", "INIT_DRY_RUN_REPORT_LIMIT", 20, ENGINE_INVARIANT, "bounded CLI display"),
    Threshold("hydra_engine.commands.installation", "RECLAIM_UNMANAGED_REPORT_LIMIT", 10, ENGINE_INVARIANT, "bounded CLI display"),
    Threshold("hydra_engine.commands.intake", "MIGRATION_INVENTORY_FINDING_REPORT_LIMIT", 20, ENGINE_INVARIANT, "bounded CLI display"),
    Threshold("hydra_engine.commands.takeover", "TAKEOVER_FINDING_REPORT_LIMIT", 10, ENGINE_INVARIANT, "bounded CLI display"),
    Threshold("hydra_engine.identity.schema_versions", "CURRENT_SCHEMA_VERSION", 3, ENGINE_INVARIANT, "object envelope schema version"),
    Threshold("hydra_engine.identity.schema_versions", "ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION", 3, ENGINE_INVARIANT, "object envelope schema version"),
    Threshold("hydra_engine.identity.schema_versions", "UID_REQUIRED_FROM_SCHEMA_VERSION", 2, ENGINE_INVARIANT, "object envelope schema version"),
    Threshold("hydra_engine.identity.schema_versions", "UNVERSIONED_SCHEMA_VERSION", 0, ENGINE_INVARIANT, "object envelope schema version"),
    Threshold("hydra_engine.intake.classification", "MIGRATION_PEEK_BYTES", 65536, ENGINE_INVARIANT, "migration source classification sample size"),
    Threshold("hydra_engine.knowledge.candidates", "APPROX_CHARS_PER_TOKEN", 4, TEAM_TUNABLE_POLICY, "context budget token approximation"),
    Threshold("hydra_engine.knowledge.candidates", "UNIT_PRIORITY", 15, ENGINE_INVARIANT, "context candidate ordering"),
    Threshold("hydra_engine.knowledge.candidates", "UNIT_READ_PRIORITY", 25, ENGINE_INVARIANT, "context candidate ordering"),
    Threshold("hydra_engine.knowledge.context_packets", "DEFAULT_CONTEXT_BUDGET", 12000, TEAM_TUNABLE_POLICY, "compile-context budget default"),
    Threshold("hydra_engine.knowledge.context_packets", "EXPLICIT_OBJECT_PRIORITY", 0, ENGINE_INVARIANT, "context candidate ordering"),
    Threshold("hydra_engine.knowledge.context_packets", "EXPLICIT_PATH_PRIORITY", 5, ENGINE_INVARIANT, "context candidate ordering"),
    Threshold("hydra_engine.knowledge.context_providers", "DEFAULT_FAMILY_CANDIDATE_CAP", 8, TEAM_TUNABLE_POLICY, "compile-context per-family candidate cap"),
    Threshold("hydra_engine.knowledge.context_providers", "NODE_OVERVIEW_PRIORITY", 20, ENGINE_INVARIANT, "context candidate ordering"),
    Threshold("hydra_engine.knowledge.context_providers", "NODE_STATE_PRIORITY", 10, ENGINE_INVARIANT, "context candidate ordering"),
    Threshold("hydra_engine.knowledge.context_providers", "PROVIDER_CANDIDATE_PRIORITY", 30, ENGINE_INVARIANT, "context candidate ordering"),
    Threshold("hydra_engine.knowledge.context_providers", "PROVIDER_SEARCH_RESULT_LIMIT", 200, TEAM_TUNABLE_POLICY, "context-provider search breadth bound"),
    Threshold("hydra_engine.knowledge.package_checks", "PACKAGE_FILE_FAIL_TOKENS", 8000, TEAM_TUNABLE_POLICY, "knowledge package file-size ceiling"),
    Threshold("hydra_engine.knowledge.package_checks", "QUESTION_MAX_LENGTH", 120, ENGINE_INVARIANT, "knowledge-unit field-format constraint"),
    Threshold("hydra_engine.knowledge.routing", "MAX_ROUTED_NODES", 2, TEAM_TUNABLE_POLICY, "route-prompt implicit-match node cap"),
    Threshold("hydra_engine.knowledge.contracts", "DEFAULT_DEPTH", 3, ENGINE_INVARIANT, "default browseability depth"),
    Threshold("hydra_engine.knowledge.contracts", "MAX_DEPTH", 4, ENGINE_INVARIANT, "hard accountability-tree depth ceiling"),
    Threshold("hydra_engine.knowledge.routing", "MIN_CONTEXT_TERM_LENGTH", 2, ENGINE_INVARIANT, "package route scoring heuristic"),
    Threshold("hydra_engine.knowledge.routing", "MIN_PLURAL_STEM_LENGTH", 3, ENGINE_INVARIANT, "package route scoring heuristic"),
    Threshold("hydra_engine.knowledge.routing", "MIN_ROUTE_MATCH_SCORE", 2, ENGINE_INVARIANT, "package route scoring heuristic"),
    Threshold("hydra_engine.knowledge.search_index", "DEFAULT_BUDGET", 2000, TEAM_TUNABLE_POLICY, "knowledge-search budget default"),
    Threshold("hydra_engine.knowledge.search_index", "DEFAULT_PREVIEW_CHARS", 280, TEAM_TUNABLE_POLICY, "knowledge-search snippet preview default"),
    Threshold("hydra_engine.knowledge.search_index", "DEFAULT_RESULT_LIMIT", 20, TEAM_TUNABLE_POLICY, "knowledge-search result limit default"),
    Threshold("hydra_engine.telemetry.gate", "GATE_MAX_SPILLOVER_PER_1000", 50, TEAM_TUNABLE_POLICY, "telemetry redaction gate spillover ceiling"),
    Threshold("hydra_engine.telemetry.gate", "GATE_MIN_EVENT_COUNT", 3, TEAM_TUNABLE_POLICY, "telemetry redaction gate corpus floor"),
    Threshold("hydra_engine.telemetry.gate", "GATE_MIN_EVENT_KINDS", 3, TEAM_TUNABLE_POLICY, "telemetry redaction gate event-kind diversity floor"),
    Threshold("hydra_engine.telemetry.evidence", "STALE_OPEN_TELEMETRY_EVIDENCE_DAYS", 30, TEAM_TUNABLE_POLICY, "telemetry evidence queue open-package staleness policy"),
    Threshold("hydra_engine.telemetry.evidence", "TELEMETRY_EVIDENCE_PACKAGE_FAIL_TOKENS", 3000, TEAM_TUNABLE_POLICY, "telemetry evidence package size ceiling"),
    Threshold("hydra_engine.telemetry.evidence", "TELEMETRY_EVIDENCE_QUEUE_DEPTH_NOTE", 10, TEAM_TUNABLE_POLICY, "telemetry evidence queue readability backstop"),
    Threshold("hydra_engine.telemetry.writer", "TELEMETRY_EVENTS_GROWTH_ADVISORY_LINES", 5000, TEAM_TUNABLE_POLICY, "append-only telemetry events log readability backstop"),
    Threshold("hydra_engine.objects.store_queries", "DEFAULT_IMPACT_DEPTH", 5, ENGINE_INVARIANT, "bounded relation-graph traversal"),
    Threshold("hydra_engine.ports.git", "GIT_ADD_TIMEOUT_SECONDS", 15, ENGINE_INVARIANT, "bounded git subprocess call"),
    Threshold("hydra_engine.ports.git", "GIT_CHECK_IGNORE_TIMEOUT_SECONDS", 15, ENGINE_INVARIANT, "bounded git subprocess call"),
    Threshold("hydra_engine.ports.git", "GIT_CONFIG_TIMEOUT_SECONDS", 5, ENGINE_INVARIANT, "bounded git subprocess call"),
    Threshold("hydra_engine.ports.git", "GIT_DIFF_TIMEOUT_SECONDS", 15, ENGINE_INVARIANT, "bounded git subprocess call"),
    Threshold("hydra_engine.ports.git", "GIT_LOG_TIMEOUT_SECONDS", 15, ENGINE_INVARIANT, "bounded git subprocess call"),
    Threshold("hydra_engine.ports.git", "GIT_LS_FILES_TIMEOUT_SECONDS", 15, ENGINE_INVARIANT, "bounded git subprocess call"),
    Threshold("hydra_engine.ports.git", "GIT_STATUS_TIMEOUT_SECONDS", 15, ENGINE_INVARIANT, "bounded git subprocess call"),
    Threshold("hydra_engine.seed.candidate_queue", "STALE_PROPOSED_CANDIDATE_DAYS", 30, TEAM_TUNABLE_POLICY, "candidate-queue proposed-item staleness policy"),
    Threshold("hydra_engine.seed.reflections", "REFLECTION_PACKET_FAIL_TOKENS", 1200, TEAM_TUNABLE_POLICY, "reflection packet size ceiling"),
    Threshold("hydra_engine.seed.reflections", "REFLECTION_QUEUE_DEPTH_NOTE", 20, TEAM_TUNABLE_POLICY, "reflection queue readability backstop"),
    Threshold("hydra_engine.seed.reflections", "STALE_REFLECTION_DAYS", 30, TEAM_TUNABLE_POLICY, "reflection packet staleness policy"),
    Threshold("hydra_engine.work.board", "STATE_POINTER_TASK_NAME_LIMIT", 3, ENGINE_INVARIANT, "bounded per-prompt state pointer output"),
    Threshold("hydra_engine.work.task_records", "STALE_TASK_DAYS", 14, TEAM_TUNABLE_POLICY, "personal task staleness policy"),
)

THRESHOLDS_BY_KEY = {entry.key: entry for entry in THRESHOLDS}
