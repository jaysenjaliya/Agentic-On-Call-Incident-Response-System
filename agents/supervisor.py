r"""Supervisor graph (WI-28..29) — wires the three subgraphs into one pipeline.

Approach B (PRD §6.3): a single flat ``StateGraph`` containing every node from the
three phases, chained diagnosis → root cause → remediation, with a global **kill
switch** guarding every phase boundary and a **dead letter** terminal so no run is
lost (FR-9). This reuses the exact node *functions* built and tested in Phase 2 —
only the wiring is new.

Flow (kill-switch check omitted for clarity; it guards each transition)::

    START ─► pull_logs ─► pull_metrics ─┬─► analyze_diagnosis ─► search_runbooks ─►
                                        │                        check_deployments ─►
                                        │                        analyze_root_cause ─►
                                        │                        evaluate_confidence ─�(3-branch)─►
                                        └─► handle_diagnosis_failure ─► escalate
    … execute_fix ─► verify_fix ─► close_incident ─┐
    … human_review (⏸ HITL) ──────────────────────┤
    … escalate ────────────────────────────────────┼─► finalize ─► END
    … dead_letter ─────────────────────────────────┘

Terminal guarantees: every incident ends resolved, escalated, or dead-lettered,
and ``finalize`` persists the audit trail to ``data/audit_trail/`` for every run.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

import config
from agents.diagnosis import (
    analyze_diagnosis,
    handle_diagnosis_failure,
    pull_logs,
    pull_metrics,
)
from agents.remediation import (
    close_incident,
    escalate,
    evaluate_confidence,
    execute_fix,
    human_review,
    route_after_human,
    route_after_verify,
    route_by_confidence,
    verify_fix,
)
from agents.root_cause import analyze_root_cause, check_deployments, search_runbooks
from state.schemas import IncidentState
from tools import MockGitHubAPI, MockLogAPI, MockMetricsAPI, MockRunbookSearch
from utils.audit_trail import append_audit_event, save_trail_to_file
from utils.dead_letter_queue import send_to_dlq
from utils.llm import get_llm
from utils.notifier import get_notifier


# ===========================================================================
# Kill switch (WI-29, NFR-3)
# ===========================================================================
def _killed(state: IncidentState) -> bool:
    """True if the global step budget is blown or the run was terminated."""
    return state["total_steps"] > config.MAX_TOTAL_STEPS or state.get("is_terminated", False)


def dead_letter(state: IncidentState) -> dict[str, Any]:
    """Terminal: serialize an unrecoverable run to the DLQ (WI-29, FR-7/FR-9).

    Reached by the kill switch (runaway steps) or any unrecoverable path. Reads
    the whole state; writes a DLQ file and marks the incident dead-lettered.
    """
    step = state["total_steps"] + 1
    reason = (
        "kill_switch: exceeded MAX_TOTAL_STEPS"
        if state["total_steps"] > config.MAX_TOTAL_STEPS
        else "unrecoverable: no viable path"
    )
    path = send_to_dlq(state, reason=reason)
    return {
        "total_steps": step,
        "resolution": config.RESOLUTION_DEAD_LETTERED,
        "dead_lettered": True,
        "is_terminated": True,
        "dlq_reference": str(path),
        "audit_trail": [
            append_audit_event(
                "dead_letter", "sent run to dead letter queue",
                output_summary=f"file={path.name}", decision=f"dead_lettered ({reason})",
                step_number=step,
            )
        ],
    }


def finalize(state: IncidentState) -> dict[str, Any]:
    """Terminal: persist the audit trail to disk and close out the run (NFR-1).

    Reads the full ``audit_trail``; writes ``data/audit_trail/<id>_audit.json``
    (including this event) and sets ``current_phase='done'``.
    """
    step = state["total_steps"] + 1
    event = append_audit_event(
        "finalize", "persisted incident record",
        output_summary=f"resolution={state.get('resolution') or 'unknown'}",
        decision=state.get("resolution") or "done", step_number=step,
    )
    # Save the trail *including* this finalize event so the file is complete.
    full_trail = (state.get("audit_trail") or []) + [event]
    save_trail_to_file(full_trail, state["incident_id"])
    return {"total_steps": step, "current_phase": "done", "audit_trail": [event]}


# ===========================================================================
# Routing (every transition first checks the kill switch — NFR-2 + NFR-3)
# ===========================================================================
def route_entry(state: IncidentState) -> str:
    return "dead_letter" if _killed(state) else "pull_logs"


def route_after_data(state: IncidentState) -> str:
    """Graceful degradation: analyze if ANY data arrived; else handle failure."""
    if _killed(state):
        return "dead_letter"
    if state.get("logs") or state.get("metrics"):
        return "analyze_diagnosis"
    return "handle_diagnosis_failure"


def route_after_diagnosis(state: IncidentState) -> str:
    return "dead_letter" if _killed(state) else "search_runbooks"


def route_after_diagnosis_failure(state: IncidentState) -> str:
    return "dead_letter" if _killed(state) else "escalate"


def route_after_root_cause(state: IncidentState) -> str:
    return "dead_letter" if _killed(state) else "evaluate_confidence"


def route_remediation(state: IncidentState) -> str:
    """Kill-switch-guarded wrapper around the confidence gate's 3-branch routing."""
    if _killed(state):
        return "dead_letter"
    return route_by_confidence(state)


# ===========================================================================
# SQLite checkpointer (WI-30)
# ===========================================================================
def make_sqlite_checkpointer(path: Any = None) -> Any:
    """Create a SQLite checkpointer for crash recovery + HITL pause/resume (WI-30).

    Uses a single shared connection (``check_same_thread=False``) so the saver
    persists state after every node to ``config.CHECKPOINT_DB``.
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    db_path = path if path is not None else config.CHECKPOINT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)


# ===========================================================================
# Graph builder
# ===========================================================================
def build_supervisor_graph(
    *,
    llm: Any = None,
    log_api: MockLogAPI | None = None,
    metrics_api: MockMetricsAPI | None = None,
    runbook_search: MockRunbookSearch | None = None,
    github_api: MockGitHubAPI | None = None,
    notifier: Any = None,
    checkpointer: Any = "memory",
    interrupt_hitl: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Compile the full incident-response pipeline (WI-28).

    All tools/LLM/notifier are injected (defaults build the real ones), so the
    whole pipeline is unit-testable offline. ``checkpointer``: ``"memory"``
    (default) for tests, a SQLite saver for real runs, or ``None`` to disable.
    Invocations must pass a ``config`` with a ``thread_id`` when a checkpointer is
    used.
    """
    llm = llm if llm is not None else get_llm()
    log_api = log_api if log_api is not None else MockLogAPI()
    metrics_api = metrics_api if metrics_api is not None else MockMetricsAPI()
    runbook_search = runbook_search if runbook_search is not None else MockRunbookSearch()
    github_api = github_api if github_api is not None else MockGitHubAPI()
    notifier = notifier if notifier is not None else get_notifier()

    g = StateGraph(IncidentState)

    # --- diagnosis ---
    g.add_node("pull_logs", lambda s: pull_logs(s, log_api=log_api, sleep=sleep))
    g.add_node("pull_metrics", lambda s: pull_metrics(s, metrics_api=metrics_api, sleep=sleep))
    g.add_node("analyze_diagnosis", lambda s: analyze_diagnosis(s, llm=llm))
    g.add_node("handle_diagnosis_failure", handle_diagnosis_failure)
    # --- root cause ---
    g.add_node("search_runbooks",
               lambda s: search_runbooks(s, runbook_search=runbook_search, sleep=sleep))
    g.add_node("check_deployments",
               lambda s: check_deployments(s, github_api=github_api, sleep=sleep))
    g.add_node("analyze_root_cause", lambda s: analyze_root_cause(s, llm=llm))
    # --- remediation ---
    g.add_node("evaluate_confidence", evaluate_confidence)
    g.add_node("execute_fix", execute_fix)
    g.add_node("verify_fix", verify_fix)
    g.add_node("human_review", human_review)
    g.add_node("escalate", lambda s: escalate(s, notifier=notifier))
    g.add_node("close_incident", close_incident)
    # --- supervisor infra ---
    g.add_node("dead_letter", dead_letter)
    g.add_node("finalize", finalize)

    # --- edges ---
    g.add_conditional_edges(START, route_entry,
                            {"pull_logs": "pull_logs", "dead_letter": "dead_letter"})
    g.add_edge("pull_logs", "pull_metrics")
    g.add_conditional_edges("pull_metrics", route_after_data, {
        "analyze_diagnosis": "analyze_diagnosis",
        "handle_diagnosis_failure": "handle_diagnosis_failure",
        "dead_letter": "dead_letter",
    })
    g.add_conditional_edges("analyze_diagnosis", route_after_diagnosis,
                            {"search_runbooks": "search_runbooks", "dead_letter": "dead_letter"})
    g.add_conditional_edges("handle_diagnosis_failure", route_after_diagnosis_failure,
                            {"escalate": "escalate", "dead_letter": "dead_letter"})
    g.add_edge("search_runbooks", "check_deployments")
    g.add_edge("check_deployments", "analyze_root_cause")
    g.add_conditional_edges("analyze_root_cause", route_after_root_cause, {
        "evaluate_confidence": "evaluate_confidence", "dead_letter": "dead_letter",
    })
    g.add_conditional_edges("evaluate_confidence", route_remediation, {
        "execute_fix": "execute_fix", "human_review": "human_review",
        "escalate": "escalate", "dead_letter": "dead_letter",
    })
    g.add_conditional_edges("human_review", route_after_human,
                            {"execute_fix": "execute_fix", "escalate": "escalate"})
    g.add_edge("execute_fix", "verify_fix")
    g.add_conditional_edges("verify_fix", route_after_verify,
                            {"close_incident": "close_incident", "escalate": "escalate"})
    g.add_edge("close_incident", "finalize")
    g.add_edge("escalate", "finalize")
    g.add_edge("dead_letter", "finalize")
    g.add_edge("finalize", END)

    saver = MemorySaver() if checkpointer == "memory" else checkpointer
    compile_kwargs: dict[str, Any] = {}
    if saver is not None:
        compile_kwargs["checkpointer"] = saver
    if interrupt_hitl:
        compile_kwargs["interrupt_before"] = ["human_review"]
    return g.compile(**compile_kwargs)
