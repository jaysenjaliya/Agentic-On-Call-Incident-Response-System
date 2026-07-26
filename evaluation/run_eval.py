"""Evaluation runner (WI-35) — runs all incidents through the full agent.

Runs every ``data/incidents/*.json`` through the supervisor pipeline and collects
per-incident results (outcome, severity, confidence, steps, audit completeness,
failure handling). Writes ``evaluation/results.json`` and prints the metrics table.

Hermetic by design:
    * Notifications are ALWAYS mock (a fresh ``MockNotificationService`` is injected)
      — the eval never sends real email, regardless of ``.env``.
    * Retry backoff is a no-op (fast), so injected tool failures don't add real delays.
    * Each incident's ``inject_failures`` sets the matching mock tool's failure mode.

Usage::

    uv run python -m evaluation.run_eval        # run all incidents (live LLM)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import config

try:  # UTF-8 stdout even on legacy Windows code pages
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:  # pragma: no cover
    pass
from agents.supervisor import build_supervisor_graph
from evaluation.metrics import compute_metrics, format_metrics_table
from state import create_initial_state
from tools import (
    FailureMode,
    MockGitHubAPI,
    MockLogAPI,
    MockMetricsAPI,
    MockNotificationService,
    MockRunbookSearch,
)

_NOOP = lambda *_: None  # noqa: E731 - fast, no real backoff sleeps

RESULTS_PATH = config.PROJECT_ROOT / "evaluation" / "results.json"

# Map an incident's inject_failures source -> which tool gets the failure mode.
_SOURCE_TO_TOOL = {"logs", "metrics", "runbooks", "deployments"}


def _build_tools(inject: dict[str, str]) -> dict[str, Any]:
    """Construct the four data tools, applying any injected failure modes."""
    def mode(source: str) -> FailureMode:
        return FailureMode(inject[source]) if source in inject else FailureMode.NONE

    return {
        "log_api": MockLogAPI(mode("logs")),
        "metrics_api": MockMetricsAPI(mode("metrics")),
        "runbook_search": MockRunbookSearch(mode("runbooks")),
        "github_api": MockGitHubAPI(mode("deployments")),
    }


def run_one(alert: dict[str, Any]) -> dict[str, Any]:
    """Run a single incident end-to-end and return a structured result record."""
    inject = alert.get("inject_failures", {})
    notifier = MockNotificationService()
    graph = build_supervisor_graph(
        notifier=notifier, checkpointer="memory", sleep=_NOOP, **_build_tools(inject)
    )

    state = create_initial_state(alert)
    cfg = {"configurable": {"thread_id": state["incident_id"]}}
    out = graph.invoke(state, cfg)

    # Simulate a reasonable human at the HITL checkpoint so eval never stalls:
    # approve the auto-fix only when a runbook actually matched (a known remedy
    # exists); otherwise reject → escalate. Mirrors real reviewer judgment.
    hitl_fired = graph.get_state(cfg).next == ("human_review",)
    hitl_decision = None
    if hitl_fired:
        paused = graph.get_state(cfg).values
        hitl_decision = "approve" if paused.get("matched_runbook_id") else "reject"
        graph.update_state(cfg, {"human_decision": hitl_decision})
        out = graph.invoke(None, cfg)

    return {
        "incident_id": out["incident_id"],
        "service": out["service_name"],
        "category": alert.get("category", "unknown"),
        "expected_outcome": alert.get("expected_outcome", "unknown"),
        "actual_outcome": out["resolution"],
        "severity": out["severity"],
        "confidence": round(out["root_cause_confidence"], 3),
        "steps": out["total_steps"],
        "audit_events": len(out["audit_trail"]),
        "data_sources_failed": out["data_sources_failed"],
        "injected_failures": inject,
        "hitl_fired": hitl_fired,
        "hitl_decision": hitl_decision,
        "dead_lettered": out["dead_lettered"],
        "notifications_sent": len(notifier.sent),
        "matched_runbook": out["matched_runbook_id"],
    }


def run_all(incident_dir: Path | None = None, pace_seconds: float = 1.5) -> list[dict[str, Any]]:
    """Run every incident JSON in ``incident_dir`` (default data/incidents/).

    ``pace_seconds`` inserts a short gap between incidents to stay within the LLM
    provider's rate limits (LLM calls also retry transient 429s internally).
    """
    directory = incident_dir if incident_dir is not None else config.INCIDENTS_DIR
    files = sorted(directory.glob("incident_*.json"))
    results: list[dict[str, Any]] = []
    print(f"Running {len(files)} incidents through the agent "
          f"(provider={config.LLM_PROVIDER}, notifications=mock)...\n")
    for i, path in enumerate(files):
        if i and pace_seconds:
            time.sleep(pace_seconds)
        alert = json.loads(path.read_text(encoding="utf-8"))
        result = run_one(alert)
        results.append(result)
        ok = "OK " if result["actual_outcome"] == result["expected_outcome"] else "DIFF"
        print(f"  [{ok}] {result['incident_id']:8} {result['category']:13} "
              f"{result['actual_outcome']:13} (exp {result['expected_outcome']:9}) "
              f"sev={result['severity']} conf={result['confidence']:.2f} steps={result['steps']}")
    return results


def main() -> None:
    """Run the full evaluation, persist results, and print the metrics table."""
    results = run_all()
    metrics = compute_metrics(results)

    RESULTS_PATH.write_text(
        json.dumps({"results": results, "metrics": metrics}, indent=2), encoding="utf-8"
    )
    print(f"\nResults written to {RESULTS_PATH.relative_to(config.PROJECT_ROOT)}\n")
    print(format_metrics_table(metrics))


if __name__ == "__main__":
    main()
