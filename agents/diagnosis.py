r"""Diagnosis subgraph (WI-11..16) — the first stage of incident response.

Pulls logs and metrics for the alerting service, then produces a structured
diagnosis (failing component, blast radius, severity P0-P3). Demonstrates the
mandatory tool-node pattern and graceful degradation: if one data source fails
but another succeeds, it still diagnoses on partial data; only if BOTH fail does
it route to failure handling (PRD §6.2).

Graph shape::

    START -> pull_logs -> pull_metrics -> (route) -> analyze_diagnosis -> END
                                                  \-> handle_diagnosis_failure -> END

Nodes take their tools/LLM via the graph builder (dependency injection), so each
node is unit-testable in isolation with mocks/stubs and no network.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

import config
from agents._common import apply_tool_outcome
from state.schemas import IncidentState
from tools import MockLogAPI, MockMetricsAPI
from tools.mock_log_api import LOG_ENTRY_KEYS
from tools.mock_metrics_api import METRIC_KEYS
from utils.audit_trail import append_audit_event
from utils.llm import get_llm, invoke_structured
from utils.tool_runner import run_tool


# ===========================================================================
# LLM output schema
# ===========================================================================
class DiagnosisResult(BaseModel):
    """Structured diagnosis the LLM must return (FR-2)."""

    failing_component: str = Field(description="The specific component/subsystem that is failing.")
    blast_radius: str = Field(description="Scope of impact: who/what is affected and how widely.")
    severity: str = Field(description="Exactly one of P0, P1, P2, P3 (see the rubric).")
    summary: str = Field(description="One or two sentences summarizing the diagnosis.")


_SEVERITY_RUBRIC = (
    "Severity rubric:\n"
    "  P0 = complete outage, data loss/corruption, or financial/security impact.\n"
    "  P1 = major degradation or high error rate on a critical user-facing service.\n"
    "  P2 = partial or moderate degradation, limited scope.\n"
    "  P3 = minor or cosmetic, negligible user impact."
)


# ===========================================================================
# Tool-calling nodes (WI-11, WI-12)
# ===========================================================================
def pull_logs(
    state: IncidentState,
    *,
    log_api: MockLogAPI,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Pull recent logs for the alerting service (WI-11).

    Reads: ``service_name``. Writes: ``logs`` on success, plus the standard
    control/audit fields. Decision: on failure, degrade and continue (the
    subgraph proceeds as long as any data source succeeds).
    """
    outcome = run_tool(
        "MockLogAPI",
        lambda: log_api.fetch_logs(state["service_name"]),
        required_keys=LOG_ENTRY_KEYS,
        sleep=sleep,
    )
    return apply_tool_outcome(
        state, node_name="pull_logs", tool_name="MockLogAPI", source="logs",
        outcome=outcome, success_fields=lambda data: {"logs": data},
        success_action="pulled recent logs", failure_action="failed to pull logs",
    )


def pull_metrics(
    state: IncidentState,
    *,
    metrics_api: MockMetricsAPI,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Pull current metrics for the alerting service (WI-12).

    Reads: ``service_name``. Writes: ``metrics`` on success, plus control/audit
    fields. Decision: on failure, degrade and continue.
    """
    outcome = run_tool(
        "MockMetricsAPI",
        lambda: metrics_api.get_metrics(state["service_name"]),
        required_keys=METRIC_KEYS,
        sleep=sleep,
    )
    return apply_tool_outcome(
        state, node_name="pull_metrics", tool_name="MockMetricsAPI", source="metrics",
        outcome=outcome, success_fields=lambda data: {"metrics": data},
        success_action="pulled current metrics", failure_action="failed to pull metrics",
    )


# ===========================================================================
# LLM analysis node (WI-13)
# ===========================================================================
def _build_diagnosis_prompt(state: IncidentState) -> str:
    """Assemble the diagnosis prompt from whatever data was collected."""
    logs = state.get("logs")
    metrics = state.get("metrics")
    log_block = "\n".join(
        f"  [{e.get('level')}] {e.get('message')}" for e in (logs or [])
    ) or "  (logs unavailable)"
    metrics_block = (
        ", ".join(f"{k}={v}" for k, v in metrics.items() if k != "service")
        if metrics else "(metrics unavailable)"
    )
    return (
        "You are a senior SRE performing first-response incident diagnosis.\n\n"
        f"ALERT: service={state['service_name']} metric={state['metric']} "
        f"violation={state['threshold_violation']}\n\n"
        f"RECENT LOGS:\n{log_block}\n\n"
        f"CURRENT METRICS: {metrics_block}\n\n"
        f"{_SEVERITY_RUBRIC}\n\n"
        "Identify the failing component, the blast radius, assign a severity, and "
        "summarize. Base the severity strictly on the rubric and the evidence."
    )


def analyze_diagnosis(
    state: IncidentState,
    *,
    llm: BaseChatModel,
) -> dict[str, Any]:
    """Produce a structured diagnosis via the LLM (WI-13, FR-2).

    Reads: ``logs``, ``metrics``, and the alert fields. Writes:
    ``diagnosis_summary``, ``failing_component``, ``blast_radius``, ``severity``.
    Decision: assigns the P0-P3 severity that later gates remediation. Wraps the
    LLM call in try/except with a safe fallback (PRD §7.2).
    """
    step = state["total_steps"] + 1
    prompt = _build_diagnosis_prompt(state)

    try:
        result = cast(DiagnosisResult, invoke_structured(llm, DiagnosisResult, prompt))
        severity = (
            result.severity if result.severity in config.SEVERITY_LEVELS
            else config.DEFAULT_SEVERITY
        )
        return {
            "total_steps": step,
            "diagnosis_summary": result.summary,
            "failing_component": result.failing_component,
            "blast_radius": result.blast_radius,
            "severity": severity,
            "current_phase": "root_cause",
            "audit_trail": [
                append_audit_event(
                    "analyze_diagnosis", "diagnosed incident",
                    tool_used=f"llm:{config.LLM_PROVIDER}",
                    input_summary=f"logs={'y' if state.get('logs') else 'n'}, "
                                  f"metrics={'y' if state.get('metrics') else 'n'}",
                    output_summary=f"component={result.failing_component}",
                    decision=f"severity={severity}", step_number=step,
                )
            ],
        }
    except Exception as exc:  # noqa: BLE001 - LLM/parse failures must not crash the graph
        return {
            "total_steps": step,
            "diagnosis_summary": f"diagnosis unavailable (LLM error: {type(exc).__name__})",
            "severity": config.DEFAULT_SEVERITY,
            "current_phase": "root_cause",
            "audit_trail": [
                append_audit_event(
                    "analyze_diagnosis", "diagnosis LLM call failed",
                    tool_used=f"llm:{config.LLM_PROVIDER}", error=str(exc)[:200],
                    decision="degrade: proceed with default severity", step_number=step,
                )
            ],
        }


# ===========================================================================
# Failure handler (WI-14)
# ===========================================================================
def handle_diagnosis_failure(state: IncidentState) -> dict[str, Any]:
    """Handle the case where ALL diagnostic data sources failed (WI-14, FR-9).

    Reads: ``data_sources_failed``. Writes: sets ``should_escalate`` and routes
    toward escalation — a diagnosis with no data is not safe to auto-act on.
    Appends one audit event.
    """
    step = state["total_steps"] + 1
    failed = ", ".join(state.get("data_sources_failed") or []) or "all"
    return {
        "total_steps": step,
        "should_escalate": True,
        "next_action": "escalate",
        "diagnosis_summary": f"diagnosis failed: no data available (failed sources: {failed})",
        "current_phase": "remediation",
        "audit_trail": [
            append_audit_event(
                "handle_diagnosis_failure", "all data sources failed",
                input_summary=f"failed={failed}",
                decision="escalate: cannot diagnose without data", step_number=step,
            )
        ],
    }


# ===========================================================================
# Routing (NFR-2: reads explicit state fields)
# ===========================================================================
def route_after_data(state: IncidentState) -> str:
    """Decide whether to analyze or escalate, based on collected data.

    Graceful degradation: proceed to ``analyze_diagnosis`` if EITHER logs or
    metrics are present; only route to ``handle_diagnosis_failure`` if both are
    absent.
    """
    if state.get("logs") or state.get("metrics"):
        return "analyze_diagnosis"
    return "handle_diagnosis_failure"


# ===========================================================================
# Graph builder
# ===========================================================================
def build_diagnosis_graph(
    *,
    llm: BaseChatModel | None = None,
    log_api: MockLogAPI | None = None,
    metrics_api: MockMetricsAPI | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Compile the diagnosis subgraph with its tools and LLM injected.

    Defaults construct the real mock tools and the configured LLM; tests pass
    stubs. Returns a compiled LangGraph ``StateGraph``.
    """
    llm = llm if llm is not None else get_llm()
    log_api = log_api if log_api is not None else MockLogAPI()
    metrics_api = metrics_api if metrics_api is not None else MockMetricsAPI()

    graph = StateGraph(IncidentState)
    graph.add_node("pull_logs", lambda s: pull_logs(s, log_api=log_api, sleep=sleep))
    graph.add_node("pull_metrics", lambda s: pull_metrics(s, metrics_api=metrics_api, sleep=sleep))
    graph.add_node("analyze_diagnosis", lambda s: analyze_diagnosis(s, llm=llm))
    graph.add_node("handle_diagnosis_failure", handle_diagnosis_failure)

    graph.add_edge(START, "pull_logs")
    graph.add_edge("pull_logs", "pull_metrics")
    graph.add_conditional_edges(
        "pull_metrics", route_after_data,
        {"analyze_diagnosis": "analyze_diagnosis",
         "handle_diagnosis_failure": "handle_diagnosis_failure"},
    )
    graph.add_edge("analyze_diagnosis", END)
    graph.add_edge("handle_diagnosis_failure", END)
    return graph.compile()
