r"""Remediation subgraph (WI-22..27) — the third stage, where the agent acts.

Confidence-gated three-branch routing (FR-4, novelty #2):

    evaluate_confidence ─┬─ auto_fix      → execute_fix → verify_fix ─┬─ close_incident (resolved)
                         │                                            └─ escalate (verify failed)
                         ├─ human_review  → (HITL pause) ─┬─ approve → execute_fix → ...
                         │                                └─ reject  → escalate
                         └─ escalate      → escalate (P0, or confidence below floor)

Gating rule (FR-4): P0 never auto-resolves regardless of confidence;
confidence > 0.85 → auto-fix; 0.50–0.85 → human review; < 0.50 → escalate.

The human_review checkpoint uses LangGraph's ``interrupt_before`` (FR-6): the graph
pauses before that node so a human can inspect full context and set
``human_decision`` before resuming. A checkpointer is required for pause/resume;
this builder defaults to an in-memory saver (Phase 3 swaps in SQLite).
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

import config
from state.schemas import IncidentState
from tools import MockNotificationService
from utils.audit_trail import append_audit_event, format_trail_for_human


# ===========================================================================
# Decision node (WI-22)
# ===========================================================================
def evaluate_confidence(state: IncidentState) -> dict[str, Any]:
    """Choose the remediation branch from confidence AND severity (WI-22, FR-4).

    Reads: ``root_cause_confidence`` and ``severity``. Writes: ``next_action``
    (auto_fix | human_review | escalate), ``needs_human_review``,
    ``should_escalate``. Decision: this is the confidence gate — deterministic,
    reading explicit typed fields only (NFR-2). P0 never auto-resolves.
    """
    step = state["total_steps"] + 1
    severity = state["severity"]
    confidence = state["root_cause_confidence"]

    if severity in config.NO_AUTO_RESOLVE_SEVERITIES:
        action, reason = "escalate", f"{severity} never auto-resolves"
    elif confidence > config.AUTO_FIX_THRESHOLD:
        action, reason = "auto_fix", f"confidence {confidence:.2f} > {config.AUTO_FIX_THRESHOLD}"
    elif confidence >= config.HITL_LOWER_THRESHOLD:
        action, reason = "human_review", (
            f"confidence {confidence:.2f} in "
            f"[{config.HITL_LOWER_THRESHOLD}, {config.AUTO_FIX_THRESHOLD}]"
        )
    else:
        action, reason = "escalate", f"confidence {confidence:.2f} < {config.HITL_LOWER_THRESHOLD}"

    return {
        "total_steps": step,
        "next_action": action,
        "needs_human_review": action == "human_review",
        "should_escalate": action == "escalate",
        "audit_trail": [
            append_audit_event(
                "evaluate_confidence", "gated remediation on confidence + severity",
                input_summary=f"severity={severity}, confidence={confidence:.2f}",
                decision=f"{action} ({reason})", confidence=confidence, step_number=step,
            )
        ],
    }


# ===========================================================================
# Auto-fix path (WI-23)
# ===========================================================================
def _matched_runbook(state: IncidentState) -> dict[str, Any] | None:
    """Return the runbook dict identified by ``matched_runbook_id``, if present."""
    rid = state.get("matched_runbook_id")
    for match in state.get("runbook_matches") or []:
        if match.get("runbook_id") == rid:
            return match
    return None


def execute_fix(state: IncidentState) -> dict[str, Any]:
    """Apply the matched runbook's remediation steps (WI-23, FR-4).

    Reads: ``matched_runbook_id`` / ``runbook_matches``. Writes:
    ``remediation_action``, ``remediation_steps``, ``fix_applied``. This is a
    mock execution (PRD §4.2) — it records what would run, without side effects.
    """
    step = state["total_steps"] + 1
    runbook = _matched_runbook(state)
    steps = list(runbook.get("remediation_steps", [])) if runbook else []
    action = (
        f"Applied runbook {runbook['runbook_id']} ({runbook['title']})"
        if runbook else "Applied generic remediation (no matched runbook)"
    )
    return {
        "total_steps": step,
        "remediation_action": action,
        "remediation_steps": steps,
        "fix_applied": True,
        "audit_trail": [
            append_audit_event(
                "execute_fix", "executed remediation",
                input_summary=f"runbook={state.get('matched_runbook_id')}",
                output_summary=f"{len(steps)} step(s) applied",
                decision="auto-fix", step_number=step,
            )
        ],
    }


def verify_fix(state: IncidentState) -> dict[str, Any]:
    """Verify the applied fix resolved the incident (WI-23).

    Reads: ``fix_applied``. Writes: ``fix_verified``. Mock verification: a fix
    that was applied is treated as successful. Decision: drives close vs escalate.
    """
    step = state["total_steps"] + 1
    verified = bool(state.get("fix_applied"))
    return {
        "total_steps": step,
        "fix_verified": verified,
        "audit_trail": [
            append_audit_event(
                "verify_fix", "verified remediation",
                output_summary=f"verified={verified}",
                decision="close" if verified else "escalate: verification failed",
                step_number=step,
            )
        ],
    }


# ===========================================================================
# HITL checkpoint (WI-24, FR-6)
# ===========================================================================
def human_review(state: IncidentState) -> dict[str, Any]:
    """Human-in-the-loop checkpoint (WI-24, FR-6, novelty #2).

    Reads: ``human_decision`` (set by a human during the interrupt) plus the full
    diagnostic context. Writes: ``next_action`` (auto_fix on approve, escalate on
    reject), ``human_review_notes``. The graph is configured to pause *before*
    this node via ``interrupt_before`` so a reviewer sees context, not a raw
    output. Absent a decision, it fails safe by escalating.
    """
    step = state["total_steps"] + 1
    decision = (state.get("human_decision") or "").lower()
    approved = decision == "approve"
    action = "auto_fix" if approved else "escalate"
    context = format_trail_for_human(state.get("audit_trail") or [])

    return {
        "total_steps": step,
        "next_action": action,
        "should_escalate": not approved,
        "human_review_notes": f"decision={decision or 'none'}",
        "audit_trail": [
            append_audit_event(
                "human_review", "human reviewed diagnosis",
                input_summary=f"confidence={state['root_cause_confidence']:.2f}, "
                              f"severity={state['severity']}",
                output_summary=f"context_lines={len(context.splitlines())}",
                decision=f"human {decision or 'no-decision'} -> {action}", step_number=step,
            )
        ],
    }


# ===========================================================================
# Terminal nodes (WI-25, FR-9)
# ===========================================================================
def escalate(state: IncidentState, *, notifier: MockNotificationService) -> dict[str, Any]:
    """Notify a human with full context and mark the incident escalated (WI-25, FR-9).

    Reads: diagnosis/root-cause fields. Writes: ``resolution='escalated'`` and
    sends a notification (mock in Phase 2; real Gmail MCP in Phase 3). Wrapped so
    a notification failure still terminates the incident cleanly.
    """
    step = state["total_steps"] + 1
    subject = f"[{state['severity']}] Incident {state['incident_id']} needs a human"
    body = (
        f"Service: {state['service_name']}\n"
        f"Diagnosis: {state.get('diagnosis_summary')}\n"
        f"Root cause: {state.get('root_cause_hypothesis')} "
        f"(confidence {state['root_cause_confidence']:.2f})\n"
        f"Runbook: {state.get('matched_runbook_id')}\n"
    )
    error = None
    try:
        notifier.send(config.ESCALATION_EMAIL_TO, subject, body)
    except Exception as exc:  # noqa: BLE001 - notification failure must not strand the incident
        error = f"{type(exc).__name__}: {exc}"

    return {
        "total_steps": step,
        "resolution": config.RESOLUTION_ESCALATED,
        "should_escalate": True,
        "resolution_notes": subject,
        "audit_trail": [
            append_audit_event(
                "escalate", "escalated to human", tool_used="MockNotificationService",
                output_summary=(
                    f"notified {config.ESCALATION_EMAIL_TO}" if not error else "notify failed"
                ),
                error=error, decision="escalated", step_number=step,
            )
        ],
    }


def close_incident(state: IncidentState) -> dict[str, Any]:
    """Finalize a successfully remediated incident (WI-25, FR-9).

    Reads: ``remediation_action``. Writes: ``resolution='resolved'``. Terminal
    success state — every incident ends resolved, escalated, or dead-lettered.
    """
    step = state["total_steps"] + 1
    return {
        "total_steps": step,
        "resolution": config.RESOLUTION_RESOLVED,
        "resolution_notes": state.get("remediation_action", "resolved"),
        "audit_trail": [
            append_audit_event(
                "close_incident", "closed incident",
                output_summary="resolution=resolved", decision="resolved", step_number=step,
            )
        ],
    }


# ===========================================================================
# Routing (NFR-2)
# ===========================================================================
def route_by_confidence(state: IncidentState) -> str:
    """Map ``next_action`` from evaluate_confidence to the first node of a branch."""
    return {
        "auto_fix": "execute_fix",
        "human_review": "human_review",
        "escalate": "escalate",
    }[state["next_action"]]


def route_after_human(state: IncidentState) -> str:
    """After HITL: approve → execute_fix, otherwise → escalate."""
    return "execute_fix" if state.get("next_action") == "auto_fix" else "escalate"


def route_after_verify(state: IncidentState) -> str:
    """After verification: verified → close_incident, else → escalate."""
    return "close_incident" if state.get("fix_verified") else "escalate"


# ===========================================================================
# Graph builder
# ===========================================================================
def build_remediation_graph(
    *,
    notifier: MockNotificationService | None = None,
    checkpointer: Any = "memory",
    interrupt_hitl: bool = True,
) -> Any:
    """Compile the remediation subgraph with three-branch routing + HITL.

    ``checkpointer``: ``"memory"`` (default) uses an in-memory saver so the HITL
    interrupt can pause/resume; pass ``None`` to disable, or a real checkpointer
    (Phase 3 SQLite). ``interrupt_hitl`` toggles the ``interrupt_before`` pause on
    ``human_review``. Invocations must pass a ``config`` with a ``thread_id`` when
    a checkpointer is used.
    """
    notifier = notifier if notifier is not None else MockNotificationService()

    graph = StateGraph(IncidentState)
    graph.add_node("evaluate_confidence", evaluate_confidence)
    graph.add_node("execute_fix", execute_fix)
    graph.add_node("verify_fix", verify_fix)
    graph.add_node("human_review", human_review)
    graph.add_node("escalate", lambda s: escalate(s, notifier=notifier))
    graph.add_node("close_incident", close_incident)

    graph.add_edge(START, "evaluate_confidence")
    graph.add_conditional_edges(
        "evaluate_confidence", route_by_confidence,
        {"execute_fix": "execute_fix", "human_review": "human_review", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "human_review", route_after_human,
        {"execute_fix": "execute_fix", "escalate": "escalate"},
    )
    graph.add_edge("execute_fix", "verify_fix")
    graph.add_conditional_edges(
        "verify_fix", route_after_verify,
        {"close_incident": "close_incident", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    graph.add_edge("close_incident", END)

    saver = MemorySaver() if checkpointer == "memory" else checkpointer
    compile_kwargs: dict[str, Any] = {}
    if saver is not None:
        compile_kwargs["checkpointer"] = saver
    if interrupt_hitl:
        compile_kwargs["interrupt_before"] = ["human_review"]
    return graph.compile(**compile_kwargs)
