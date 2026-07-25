r"""Root-cause subgraph (WI-17..21) — the second stage of incident response.

Searches the runbook knowledge base for matching incident patterns and checks
recent deployments for a regression trigger, then produces a root-cause
hypothesis with a calibrated confidence score (0.0-1.0) that later gates
remediation (FR-3, FR-4).

Graph shape::

    START -> search_runbooks -> check_deployments -> analyze_root_cause -> END

Graceful degradation: the analysis node reasons over whatever was gathered. No
runbook match legitimately yields LOW confidence, which drives escalation
downstream — exactly the intended behaviour for novel incidents.
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
from tools import MockGitHubAPI, MockRunbookSearch
from tools.mock_github_api import DEPLOYMENT_KEYS
from utils.audit_trail import append_audit_event
from utils.llm import get_llm
from utils.tool_runner import run_tool


# ===========================================================================
# LLM output schema
# ===========================================================================
class RootCauseResult(BaseModel):
    """Structured root-cause analysis the LLM must return (FR-3)."""

    hypothesis: str = Field(description="The most likely root cause, stated concisely.")
    confidence: float = Field(description="Confidence 0.0-1.0 that the hypothesis is correct.")
    matched_runbook_id: str | None = Field(
        default=None, description="ID of the runbook that best explains this, or null if none."
    )


_CONFIDENCE_GUIDANCE = (
    "Confidence calibration (critical — remediation is gated on this):\n"
    "  - A clearly matching runbook AND an aligning suspect deployment -> HIGH (0.85-0.98).\n"
    "  - A matching runbook OR a suspect deployment, but not both -> MEDIUM (0.5-0.85).\n"
    "  - No matching runbook and no obvious regression -> LOW (0.0-0.5).\n"
    "Never report high confidence without concrete supporting evidence."
)


# ===========================================================================
# Tool-calling nodes (WI-17, WI-18)
# ===========================================================================
def _build_runbook_query(state: IncidentState) -> str:
    """Compose a keyword-rich query from the diagnosis + alert + log signal."""
    log_text = " ".join(
        str(e.get("message", "")) for e in (state.get("logs") or [])
    )
    parts = [
        state.get("service_name", ""), state.get("metric", ""),
        state.get("failing_component", ""), state.get("diagnosis_summary", ""),
        state.get("threshold_violation", ""), log_text,
    ]
    return " ".join(p for p in parts if p)


def search_runbooks(
    state: IncidentState,
    *,
    runbook_search: MockRunbookSearch,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Search the runbook KB for patterns matching this incident (WI-17).

    Reads: diagnosis + alert + logs (to build the query). Writes:
    ``runbook_matches``. Decision: an empty result is valid (no known pattern)
    and legitimately steers toward escalation later.
    """
    query = _build_runbook_query(state)
    outcome = run_tool(
        "MockRunbookSearch", lambda: runbook_search.search(query), sleep=sleep,
    )
    return apply_tool_outcome(
        state, node_name="search_runbooks", tool_name="MockRunbookSearch", source="runbooks",
        outcome=outcome, success_fields=lambda data: {"runbook_matches": data},
        success_action="searched runbooks", failure_action="failed to search runbooks",
    )


def check_deployments(
    state: IncidentState,
    *,
    github_api: MockGitHubAPI,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Check recent deployments for a regression trigger (WI-18).

    Reads: ``service_name``. Writes: ``deployments`` and ``regression_deployment``
    (the first deploy flagged ``suspect``, if any).
    """
    outcome = run_tool(
        "MockGitHubAPI",
        lambda: github_api.get_recent_deployments(state["service_name"]),
        required_keys=DEPLOYMENT_KEYS,
        sleep=sleep,
    )

    def success_fields(data: list[dict[str, Any]]) -> dict[str, Any]:
        suspect = next((d for d in data if d.get("suspect")), None)
        return {"deployments": data, "regression_deployment": suspect}

    return apply_tool_outcome(
        state, node_name="check_deployments", tool_name="MockGitHubAPI", source="deployments",
        outcome=outcome, success_fields=success_fields,
        success_action="checked recent deployments", failure_action="failed to check deployments",
    )


# ===========================================================================
# LLM analysis node (WI-19)
# ===========================================================================
def _build_root_cause_prompt(state: IncidentState) -> str:
    """Assemble the root-cause prompt from runbook matches + deployments + diagnosis."""
    matches = state.get("runbook_matches") or []
    runbook_block = "\n".join(
        f"  - {m.get('runbook_id')}: {m.get('title')} "
        f"(root_cause: {m.get('root_cause')}, score={m.get('score')})"
        for m in matches
    ) or "  (no runbook matched)"

    regression = state.get("regression_deployment")
    regression_block = (
        f"  {regression.get('sha')} by {regression.get('author')} "
        f"at {regression.get('timestamp')}: {regression.get('summary')}"
        if regression else "  (no suspect deployment)"
    )

    return (
        "You are a senior SRE determining the root cause of an incident.\n\n"
        f"DIAGNOSIS: {state.get('diagnosis_summary')}\n"
        f"FAILING COMPONENT: {state.get('failing_component')}\n"
        f"SEVERITY: {state.get('severity')}\n\n"
        f"MATCHING RUNBOOKS:\n{runbook_block}\n\n"
        f"SUSPECT DEPLOYMENT:\n{regression_block}\n\n"
        f"{_CONFIDENCE_GUIDANCE}\n\n"
        "State the single most likely root cause, a calibrated confidence, and the "
        "runbook id that best explains it (or null)."
    )


def analyze_root_cause(
    state: IncidentState,
    *,
    llm: BaseChatModel,
) -> dict[str, Any]:
    """Produce a root-cause hypothesis with a confidence score (WI-19, FR-3).

    Reads: ``runbook_matches``, ``regression_deployment``, diagnosis fields.
    Writes: ``root_cause_hypothesis``, ``root_cause_confidence``,
    ``matched_runbook_id``. Decision: the confidence here is what
    ``evaluate_confidence`` gates on. Clamps confidence to [0,1]; on LLM error,
    degrades to zero confidence (→ escalation).
    """
    step = state["total_steps"] + 1
    matches = state.get("runbook_matches") or []
    valid_ids = {m.get("runbook_id") for m in matches}

    try:
        result = cast(
            RootCauseResult,
            llm.with_structured_output(RootCauseResult).invoke(_build_root_cause_prompt(state)),
        )
        confidence = max(0.0, min(1.0, float(result.confidence)))
        # Trust the LLM's runbook choice only if it exists; else fall back to top match.
        runbook_id = result.matched_runbook_id if result.matched_runbook_id in valid_ids else None
        if runbook_id is None and matches:
            runbook_id = matches[0].get("runbook_id")
        return {
            "total_steps": step,
            "root_cause_hypothesis": result.hypothesis,
            "root_cause_confidence": confidence,
            "matched_runbook_id": runbook_id,
            "current_phase": "remediation",
            "audit_trail": [
                append_audit_event(
                    "analyze_root_cause", "hypothesized root cause",
                    tool_used=f"llm:{config.LLM_PROVIDER}",
                    input_summary=f"runbooks={len(matches)}, "
                                  f"suspect={'y' if state.get('regression_deployment') else 'n'}",
                    output_summary=f"runbook={runbook_id}",
                    decision=f"confidence={confidence:.2f}",
                    confidence=confidence, step_number=step,
                )
            ],
        }
    except Exception as exc:  # noqa: BLE001 - degrade, don't crash
        return {
            "total_steps": step,
            "root_cause_hypothesis": f"root cause undetermined (LLM error: {type(exc).__name__})",
            "root_cause_confidence": 0.0,
            "current_phase": "remediation",
            "audit_trail": [
                append_audit_event(
                    "analyze_root_cause", "root-cause LLM call failed",
                    tool_used=f"llm:{config.LLM_PROVIDER}", error=str(exc)[:200],
                    decision="degrade: zero confidence -> escalate",
                    confidence=0.0, step_number=step,
                )
            ],
        }


# ===========================================================================
# Graph builder
# ===========================================================================
def build_root_cause_graph(
    *,
    llm: BaseChatModel | None = None,
    runbook_search: MockRunbookSearch | None = None,
    github_api: MockGitHubAPI | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Compile the root-cause subgraph with tools and LLM injected."""
    llm = llm if llm is not None else get_llm()
    runbook_search = runbook_search if runbook_search is not None else MockRunbookSearch()
    github_api = github_api if github_api is not None else MockGitHubAPI()

    graph = StateGraph(IncidentState)
    graph.add_node(
        "search_runbooks",
        lambda s: search_runbooks(s, runbook_search=runbook_search, sleep=sleep),
    )
    graph.add_node(
        "check_deployments",
        lambda s: check_deployments(s, github_api=github_api, sleep=sleep),
    )
    graph.add_node("analyze_root_cause", lambda s: analyze_root_cause(s, llm=llm))

    graph.add_edge(START, "search_runbooks")
    graph.add_edge("search_runbooks", "check_deployments")
    graph.add_edge("check_deployments", "analyze_root_cause")
    graph.add_edge("analyze_root_cause", END)
    return graph.compile()
