"""Shared helpers for building subgraph nodes.

Keeps the tool-calling nodes uniform: each increments the global step counter,
records success/failure into the control fields, and appends exactly one audit
event (PRD §3.2). Nodes return ONLY the fields they modify.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from state.schemas import IncidentState
from utils.audit_trail import append_audit_event
from utils.tool_runner import ToolOutcome


def _summarize(data: Any, response_class: str | None) -> str:
    """Produce a short, log-safe summary of a tool response for the audit event."""
    if isinstance(data, list):
        return f"{len(data)} item(s) ({response_class})"
    if isinstance(data, dict):
        return f"{len(data)} field(s) ({response_class})"
    return f"({response_class})"


def apply_tool_outcome(
    state: IncidentState,
    *,
    node_name: str,
    tool_name: str,
    source: str,
    outcome: ToolOutcome,
    success_fields: Callable[[Any], dict[str, Any]],
    success_action: str,
    failure_action: str,
) -> dict[str, Any]:
    """Turn a :class:`ToolOutcome` into standard node state updates + one audit event.

    Reads: ``total_steps`` and the two ``data_sources_*`` lists from ``state``.
    Writes (on success): the caller's data fields (via ``success_fields``),
    appends ``source`` to ``data_sources_succeeded``. On failure: records the
    classified failure into the control fields and appends ``source`` to
    ``data_sources_failed`` (graceful degradation — the run continues).
    Always: increments ``total_steps`` and appends one ``AuditEvent``.
    """
    step = state["total_steps"] + 1
    updates: dict[str, Any] = {"total_steps": step}

    if outcome.ok:
        updates.update(success_fields(outcome.data))
        updates["data_sources_succeeded"] = state["data_sources_succeeded"] + [source]
        updates["audit_trail"] = [
            append_audit_event(
                node_name, success_action, tool_used=tool_name,
                input_summary=f"service={state['service_name']}",
                output_summary=_summarize(outcome.data, outcome.response_class),
                step_number=step,
            )
        ]
    else:
        updates["data_sources_failed"] = state["data_sources_failed"] + [source]
        updates["last_failure_type"] = outcome.failure_type
        updates["last_error"] = outcome.error
        updates["audit_trail"] = [
            append_audit_event(
                node_name, failure_action, tool_used=tool_name,
                input_summary=f"service={state['service_name']}",
                error=f"{outcome.failure_type}: {outcome.error}",
                decision="degrade: continue with remaining data",
                step_number=step,
            )
        ]
    return updates
