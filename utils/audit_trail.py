"""Audit trail — novelty feature #4: the audit trail as a first-class citizen (FR-8).

Every node appends exactly one structured ``AuditEvent`` before returning. The
resulting trail is simultaneously a debugging artifact, a post-mortem draft, and
evaluation ground truth (PRD §1.4).

Three helpers:
    append_audit_event(...)     -- build one event; return it for a node to append.
    format_trail_for_human(...) -- render a trail as readable text (for HITL/CLI).
    save_trail_to_file(...)     -- persist a trail as JSON under data/audit_trail/.

Design: ``IncidentState.audit_trail`` uses an ``operator.add`` reducer, so a node
appends by returning ``{"audit_trail": [append_audit_event(...)]}``. This helper
therefore *returns* an event rather than mutating state — keeping nodes to "return
only the fields they modify" (PRD §3.2).
"""

from __future__ import annotations

import json
from pathlib import Path

import config
from state.schemas import AuditEvent


def append_audit_event(
    node_name: str,
    action: str,
    *,
    tool_used: str | None = None,
    input_summary: str = "",
    output_summary: str = "",
    decision: str = "",
    error: str | None = None,
    confidence: float | None = None,
    step_number: int | None = None,
) -> AuditEvent:
    """Build a single structured audit event (FR-8 fields).

    Returns the ``AuditEvent`` for the caller to append to ``state['audit_trail']``
    (typically ``return {"audit_trail": [event]}`` so the reducer concatenates it).
    Named "append_*" because from a node's perspective it appends one event to the
    trail; it does not mutate global state here.
    """
    return AuditEvent(
        node_name=node_name,
        action=action,
        tool_used=tool_used,
        input_summary=input_summary,
        output_summary=output_summary,
        decision=decision,
        error=error,
        confidence=confidence,
        step_number=step_number,
    )


def format_trail_for_human(trail: list[AuditEvent]) -> str:
    """Render an audit trail as human-readable text (for HITL context and the CLI).

    Reads a list of ``AuditEvent``; returns a multi-line string. Only populated
    fields are shown per event to keep it scannable.
    """
    if not trail:
        return "(audit trail is empty)"

    lines: list[str] = []
    for i, event in enumerate(trail, start=1):
        step = f" [step {event.step_number}]" if event.step_number is not None else ""
        lines.append(f"{i:>2}. {event.node_name}{step} - {event.action}")
        if event.tool_used:
            lines.append(f"      tool:     {event.tool_used}")
        if event.input_summary:
            lines.append(f"      input:    {event.input_summary}")
        if event.output_summary:
            lines.append(f"      output:   {event.output_summary}")
        if event.decision:
            lines.append(f"      decision: {event.decision}")
        if event.confidence is not None:
            lines.append(f"      confidence: {event.confidence:.2f}")
        if event.error:
            lines.append(f"      error:    {event.error}")
        lines.append(f"      at:       {event.timestamp}")
    return "\n".join(lines)


def save_trail_to_file(
    trail: list[AuditEvent],
    incident_id: str,
    directory: Path | None = None,
) -> Path:
    """Persist an audit trail as JSON under ``data/audit_trail/`` (NFR-1 evidence).

    Reads the trail and incident id; writes ``<incident_id>_audit.json`` and
    returns its path. Creates the directory if needed. Each event is serialized
    via ``AuditEvent.model_dump()``.
    """
    target_dir = directory if directory is not None else config.AUDIT_TRAIL_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{incident_id}_audit.json"

    payload = {
        "incident_id": incident_id,
        "event_count": len(trail),
        "events": [event.model_dump() for event in trail],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
