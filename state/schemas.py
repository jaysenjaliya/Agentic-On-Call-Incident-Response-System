"""The shared, typed state contract for the entire system.

This module is the **locked contract** (PRD §4.1): every subgraph reads from and
writes to ``IncidentState``. No node may add a field without updating this schema
and getting project-lead approval (it is frozen at v0.1.0).

Contents:
    IncidentState      -- TypedDict with five field categories:
                          input · output · control · routing · logging.
    AuditEvent         -- Pydantic model; one structured event per node (FR-8).
    DeadLetterEntry    -- Pydantic model; full snapshot of a failed run (FR-7).
    create_initial_state(alert) -- factory that builds a fully-defaulted state.

Design notes:
    * ``audit_trail`` uses an ``operator.add`` reducer so graph nodes can append
      by returning ``{"audit_trail": [event]}`` (the LangGraph idiom) while
      honoring "nodes return only the fields they modify" (PRD §3.2).
    * All other fields are plain: a node that owns a field returns its new value.
"""

from __future__ import annotations

import operator
from datetime import UTC, datetime
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field

import config


# ===========================================================================
# Structured records (Pydantic)
# ===========================================================================
def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (audit timestamps)."""
    return datetime.now(UTC).isoformat()


class AuditEvent(BaseModel):
    """One structured audit record appended by every node before it returns (FR-8).

    The audit trail is a first-class novelty feature: debugging artifact,
    post-mortem draft, and evaluation ground truth simultaneously (PRD §1.4).
    """

    timestamp: str = Field(default_factory=_utc_now_iso)
    node_name: str = Field(..., description="Graph node that produced this event.")
    action: str = Field(..., description="What the node did, in a short phrase.")
    tool_used: str | None = Field(
        default=None, description="Tool invoked by the node, if any."
    )
    input_summary: str = Field(default="", description="Brief summary of inputs read.")
    output_summary: str = Field(default="", description="Brief summary of outputs written.")
    decision: str = Field(default="", description="Routing/decision the node made, if any.")
    error: str | None = Field(
        default=None, description="Error encountered (classified type + message), if any."
    )
    confidence: float | None = Field(
        default=None, description="Confidence score where applicable (0.0-1.0)."
    )
    step_number: int | None = Field(
        default=None, description="Value of total_steps when this event was logged."
    )


class DeadLetterEntry(BaseModel):
    """A serialized snapshot of a run that failed beyond recovery (FR-7).

    Written to the dead letter queue so nothing is silently lost — enough context
    for later human review or automated retry.
    """

    incident_id: str
    timestamp: str = Field(default_factory=_utc_now_iso)
    reason: str = Field(..., description="Why the run was dead-lettered.")
    failure_type: str | None = Field(
        default=None, description="Last classified failure type, if any."
    )
    last_error: str | None = Field(default=None, description="Last error message, if any.")
    total_steps: int = Field(default=0, description="Steps executed before failure.")
    state_snapshot: dict[str, Any] = Field(
        default_factory=dict, description="Full IncidentState at time of failure."
    )


# ===========================================================================
# The agent state (TypedDict) — five field categories
# ===========================================================================
class IncidentState(TypedDict):
    """Typed state threaded through every node. LOCKED at v0.1.0.

    Fields are grouped into the five categories mandated by the PRD (§6.1). A
    node reads what it needs and returns ONLY the fields it modifies.
    """

    # ---- (1) INPUT: the incoming alert (FR-1) ----
    incident_id: str
    service_name: str
    metric: str
    threshold_violation: str          # human-readable description of what breached
    alert_timestamp: str
    raw_alert: dict[str, Any]         # original alert payload, untouched

    # ---- (2) OUTPUT: data collected + analysis produced ----
    # Raw data gathered by tool-calling nodes (may be partial — graceful degradation).
    logs: list[dict[str, Any]] | None
    metrics: dict[str, Any] | None
    runbook_matches: list[dict[str, Any]]
    deployments: list[dict[str, Any]]
    # Diagnosis subgraph output (FR-2).
    diagnosis_summary: str
    failing_component: str
    blast_radius: str
    severity: str                     # one of config.SEVERITY_LEVELS (P0-P3)
    # Root-cause subgraph output (FR-3).
    root_cause_hypothesis: str
    root_cause_confidence: float      # 0.0-1.0
    matched_runbook_id: str | None
    regression_deployment: dict[str, Any] | None
    # Remediation subgraph output (FR-4).
    remediation_action: str
    remediation_steps: list[str]
    fix_applied: bool
    fix_verified: bool
    resolution: str                   # "" until terminal; then a config.RESOLUTION_* value
    resolution_notes: str

    # ---- (3) CONTROL: execution counters + error handling (FR-5, NFR-3) ----
    total_steps: int                  # global step counter for the kill switch
    retry_count: int                  # retries on the current tool call
    tool_retry_counts: dict[str, int]  # per-tool retry tallies
    last_failure_type: str | None  # config.FAILURE_* of the most recent failure
    last_error: str | None         # message of the most recent error
    data_sources_failed: list[str]    # tools that failed this run
    data_sources_succeeded: list[str]  # tools that returned usable data

    # ---- (4) ROUTING: fields conditional edges read (NFR-2) ----
    current_phase: str                # diagnosis | root_cause | remediation | done
    next_action: str                  # auto_fix | human_review | escalate | continue | ...
    needs_human_review: bool
    human_decision: str | None     # approve | reject (set by HITL resume)
    human_review_notes: str
    should_escalate: bool
    is_terminated: bool               # kill switch fired

    # ---- (5) LOGGING: audit trail + DLQ + trajectory ----
    audit_trail: Annotated[list[AuditEvent], operator.add]
    trajectory_summary: str           # reserved for Phase 5 stretch (WI-39)
    dead_lettered: bool
    dlq_reference: str | None      # path/id of the DLQ entry, if written


# ===========================================================================
# Factory
# ===========================================================================
def create_initial_state(alert: dict[str, Any]) -> IncidentState:
    """Build a fully-defaulted ``IncidentState`` from a structured alert (FR-1).

    Reads: the alert dict (service name, metric, threshold violation, timestamp,
    and optional incident_id).
    Writes: every state field, set to its appropriate default so downstream nodes
    can rely on presence rather than ``KeyError`` guards.
    Decisions: none — pure initialization.

    The alert may use either ``incident_id`` or ``id`` for its identifier; if
    neither is present a timestamp-based id is generated.
    """
    incident_id = str(
        alert.get("incident_id")
        or alert.get("id")
        or f"INC-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    )

    return IncidentState(
        # ---- input ----
        incident_id=incident_id,
        service_name=str(alert.get("service_name", "")),
        metric=str(alert.get("metric", "")),
        threshold_violation=str(alert.get("threshold_violation", "")),
        alert_timestamp=str(alert.get("timestamp", alert.get("alert_timestamp", ""))),
        raw_alert=dict(alert),
        # ---- output ----
        logs=None,
        metrics=None,
        runbook_matches=[],
        deployments=[],
        diagnosis_summary="",
        failing_component="",
        blast_radius="",
        severity=config.DEFAULT_SEVERITY,
        root_cause_hypothesis="",
        root_cause_confidence=0.0,
        matched_runbook_id=None,
        regression_deployment=None,
        remediation_action="",
        remediation_steps=[],
        fix_applied=False,
        fix_verified=False,
        resolution="",
        resolution_notes="",
        # ---- control ----
        total_steps=0,
        retry_count=0,
        tool_retry_counts={},
        last_failure_type=None,
        last_error=None,
        data_sources_failed=[],
        data_sources_succeeded=[],
        # ---- routing ----
        current_phase="diagnosis",
        next_action="continue",
        needs_human_review=False,
        human_decision=None,
        human_review_notes="",
        should_escalate=False,
        is_terminated=False,
        # ---- logging ----
        audit_trail=[],
        trajectory_summary="",
        dead_lettered=False,
        dlq_reference=None,
    )
