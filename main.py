"""CLI entry point for the Agentic Incident Response System.

Phase 1 commands (Foundation / v0.1.0):
    --test-tools    exercise all 4 mock tools across every failure mode
    --test-state    verify state creation and field defaults
    --review-dlq    print the contents of the dead letter queue

Later phases add running an incident end-to-end through the graph.

Each command prints pass/fail evidence and sets the process exit code (0 = pass,
1 = fail) so the release criteria are demonstrable and scriptable.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any

import config
from state import IncidentState, create_initial_state
from tools import (
    MockGitHubAPI,
    MockLogAPI,
    MockMetricsAPI,
    MockNotificationService,
    MockRunbookSearch,
)
from tools.base import FailureMode
from tools.mock_github_api import DEPLOYMENT_KEYS
from tools.mock_log_api import LOG_ENTRY_KEYS
from tools.mock_metrics_api import METRIC_KEYS
from tools.mock_notification import RECEIPT_KEYS
from tools.mock_runbook_search import RUNBOOK_KEYS
from utils import classify_failure, classify_response, review_dlq

# Ensure UTF-8 stdout even on legacy Windows code pages.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:  # pragma: no cover - best effort
    pass


# ---------------------------------------------------------------------------
# --test-tools
# ---------------------------------------------------------------------------
# Per-mode expectation: ("exception", <failure_type>) or ("response", <class>).
_MODE_EXPECTATIONS: dict[FailureMode, tuple[str, str]] = {
    FailureMode.NONE: ("response", config.RESPONSE_OK),
    FailureMode.TIMEOUT: ("exception", config.FAILURE_TIMEOUT),
    FailureMode.RATE_LIMIT: ("exception", config.FAILURE_RATE_LIMIT),
    FailureMode.AUTH: ("exception", config.FAILURE_AUTH),
    FailureMode.EMPTY: ("response", config.RESPONSE_EMPTY),
    FailureMode.MALFORMED: ("response", config.RESPONSE_MALFORMED),
}


_ToolSpec = tuple[str, Callable[[FailureMode], Any], Callable[[Any], Any], tuple[str, ...]]


def _tool_specs() -> list[_ToolSpec]:
    """Return (name, factory(mode), invoke(tool), required_keys) for all 4 tools."""
    return [
        ("MockLogAPI", lambda m: MockLogAPI(m), lambda t: t.fetch_logs("checkout"), LOG_ENTRY_KEYS),
        ("MockMetricsAPI", lambda m: MockMetricsAPI(m),
         lambda t: t.get_metrics("checkout"), METRIC_KEYS),
        ("MockRunbookSearch", lambda m: MockRunbookSearch(m),
         lambda t: t.search("connection pool exhausted psycopg2 database"), RUNBOOK_KEYS),
        ("MockGitHubAPI", lambda m: MockGitHubAPI(m),
         lambda t: t.get_recent_deployments("checkout"), DEPLOYMENT_KEYS),
        ("MockNotificationService", lambda m: MockNotificationService(m),
         lambda t: t.send("oncall@example.com", "INC-TEST", "body"), RECEIPT_KEYS),
    ]


def test_tools() -> bool:
    """Verify every tool works normally and every failure mode behaves correctly.

    Release criterion (v0.1.0): all 4 tools work normally; all failure modes
    raise correct exceptions / return correctly-classifiable responses.
    """
    print("== --test-tools ==\n")
    all_ok = True

    for name, factory, invoke, required_keys in _tool_specs():
        print(f"{name}")
        for mode, (kind, expected) in _MODE_EXPECTATIONS.items():
            tool = factory(mode)
            try:
                result = invoke(tool)
            except Exception as exc:  # noqa: BLE001 - classification is the point
                actual = classify_failure(exc)
                passed = kind == "exception" and actual == expected
                detail = f"raised {type(exc).__name__} -> classify_failure={actual}"
            else:
                keys = required_keys if mode == FailureMode.NONE else None
                actual = classify_response(result, required_keys=keys)
                passed = kind == "response" and actual == expected
                detail = f"returned {type(result).__name__} -> classify_response={actual}"

            all_ok &= passed
            mark = "[OK]  " if passed else "[FAIL]"
            print(f"  {mark} {mode.value:10} expect {expected:10} | {detail}")
        print()

    print("RESULT:", "PASS - all tools and failure modes behave correctly"
          if all_ok else "FAIL - see [FAIL] rows above")
    return all_ok


# ---------------------------------------------------------------------------
# --test-state
# ---------------------------------------------------------------------------
def test_state() -> bool:
    """Verify state creation: all fields present with correct defaults (FR-1).

    Release criterion (v0.1.0): state creation works, all fields present with
    correct defaults.
    """
    print("== --test-state ==\n")
    all_ok = True

    alert = {
        "incident_id": "INC-STATE-TEST",
        "service_name": "checkout",
        "metric": "error_rate",
        "threshold_violation": ">5%",
        "timestamp": "2026-07-25T02:00:00Z",
    }
    state = create_initial_state(alert)

    # 1. Every schema field is present.
    expected_fields = set(IncidentState.__annotations__.keys())
    actual_fields = set(state.keys())
    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields
    fields_ok = not missing and not extra
    all_ok &= fields_ok
    mark = "[OK]  " if fields_ok else "[FAIL]"
    print(f"  {mark} all {len(expected_fields)} schema fields present "
          f"(missing={sorted(missing)}, extra={sorted(extra)})")

    # 2. Input fields populated from the alert.
    input_ok = (
        state["incident_id"] == "INC-STATE-TEST"
        and state["service_name"] == "checkout"
        and state["metric"] == "error_rate"
        and state["raw_alert"] == alert
    )
    all_ok &= input_ok
    print(f"  {'[OK]  ' if input_ok else '[FAIL]'} input fields populated from alert")

    # 3. Defaults across the other four categories.
    default_checks: list[tuple[str, bool]] = [
        ("severity == DEFAULT_SEVERITY", state["severity"] == config.DEFAULT_SEVERITY),
        ("root_cause_confidence == 0.0", state["root_cause_confidence"] == 0.0),
        ("resolution == ''", state["resolution"] == ""),
        ("total_steps == 0", state["total_steps"] == 0),
        ("retry_count == 0", state["retry_count"] == 0),
        ("tool_retry_counts == {}", state["tool_retry_counts"] == {}),
        ("current_phase == 'diagnosis'", state["current_phase"] == "diagnosis"),
        ("needs_human_review is False", state["needs_human_review"] is False),
        ("should_escalate is False", state["should_escalate"] is False),
        ("is_terminated is False", state["is_terminated"] is False),
        ("audit_trail == []", state["audit_trail"] == []),
        ("dead_lettered is False", state["dead_lettered"] is False),
        ("logs is None", state["logs"] is None),
    ]
    for label, ok in default_checks:
        all_ok &= ok
        print(f"  {'[OK]  ' if ok else '[FAIL]'} {label}")

    print("\nRESULT:", "PASS - state initializes with correct defaults"
          if all_ok else "FAIL - see [FAIL] rows above")
    return all_ok


# ---------------------------------------------------------------------------
# --review-dlq
# ---------------------------------------------------------------------------
def review_dlq_cmd() -> bool:
    """Print the contents of the dead letter queue (FR-7)."""
    print("== --review-dlq ==\n")
    config.ensure_runtime_dirs()
    entries = review_dlq()
    if not entries:
        print(f"Dead letter queue is empty ({config.DLQ_DIR}).")
        return True

    print(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} in {config.DLQ_DIR}:\n")
    for entry in entries:
        print(f"- {entry.incident_id}  reason={entry.reason}  "
              f"failure_type={entry.failure_type}  steps={entry.total_steps}  at={entry.timestamp}")
        trail = entry.state_snapshot.get("audit_trail", [])
        print(f"    audit events in snapshot: {len(trail)}")
    return True


# ---------------------------------------------------------------------------
# run an incident end-to-end (Phase 3)
# ---------------------------------------------------------------------------
def run_incident(path: str, hitl: str | None = None) -> bool:
    """Run one incident through the full supervisor pipeline (WI-28..33).

    Loads the alert JSON, runs it through diagnosis → root cause → remediation
    with the SQLite checkpointer and (if configured) LangSmith tracing, and prints
    the outcome. If the run pauses at the HITL checkpoint, ``hitl`` (approve/reject)
    resumes it; otherwise it stays paused (resume later with --hitl).
    """
    import json
    from pathlib import Path

    from agents.supervisor import build_supervisor_graph, make_sqlite_checkpointer
    from state import create_initial_state
    from utils.audit_trail import format_trail_for_human
    from utils.observability import run_config, tracing_status

    alert_path = Path(path)
    if not alert_path.exists():
        print(f"ERROR: incident file not found: {alert_path}")
        return False

    config.ensure_runtime_dirs()
    enabled, detail = tracing_status()
    print(f"== run incident: {alert_path.name} ==")
    print(f"LLM provider: {config.LLM_PROVIDER} | LangSmith tracing: {detail}\n")

    alert = json.loads(alert_path.read_text(encoding="utf-8"))
    state = create_initial_state(alert)
    graph = build_supervisor_graph(checkpointer=make_sqlite_checkpointer())
    cfg = run_config(state["incident_id"], thread_id=state["incident_id"])

    out = graph.invoke(state, cfg)

    # Handle a HITL pause (interrupt_before human_review).
    if graph.get_state(cfg).next == ("human_review",):
        print("-- PAUSED at human_review (HITL checkpoint) --")
        print(format_trail_for_human(out["audit_trail"]))
        conf = out.get("root_cause_confidence", 0)
        print(f"\nRoot cause: {out.get('root_cause_hypothesis')} "
              f"(confidence {conf:.2f}, severity {out.get('severity')})")
        if hitl in ("approve", "reject"):
            print(f"\nApplying human decision: {hitl}")
            graph.update_state(cfg, {"human_decision": hitl})
            out = graph.invoke(None, cfg)
        else:
            print("\nRun is paused. Resume with:  "
                  f"python main.py {path} --hitl approve   (or reject)")
            return True

    print(f"RESOLUTION: {out['resolution'].upper()}  |  steps: {out['total_steps']}  "
          f"|  severity: {out['severity']}  |  confidence: {out['root_cause_confidence']:.2f}")
    print(f"audit trail: {config.AUDIT_TRAIL_DIR / (out['incident_id'] + '_audit.json')} "
          f"({len(out['audit_trail'])} events)")
    if out.get("dlq_reference"):
        print(f"dead-lettered: {out['dlq_reference']}")
    return True


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Parse CLI args and dispatch. Exits non-zero if a test command fails."""
    parser = argparse.ArgumentParser(
        prog="incident-response",
        description="Agentic On-Call Incident Response System.",
    )
    parser.add_argument("incident", nargs="?",
                        help="Path to an incident JSON to run end-to-end "
                             "(e.g. data/incidents/incident_001.json).")
    parser.add_argument("--hitl", choices=["approve", "reject"], default=None,
                        help="Resume a HITL-paused incident with this decision.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--test-tools", action="store_true",
                       help="Exercise all mock tools + failure modes.")
    group.add_argument("--test-state", action="store_true",
                       help="Verify state creation and defaults.")
    group.add_argument("--review-dlq", action="store_true",
                       help="Print the dead letter queue.")

    args = parser.parse_args()

    if args.test_tools:
        ok = test_tools()
    elif args.test_state:
        ok = test_state()
    elif args.review_dlq:
        ok = review_dlq_cmd()
    elif args.incident:
        ok = run_incident(args.incident, hitl=args.hitl)
    else:
        parser.error("provide an incident file to run, or one of "
                     "--test-tools/--test-state/--review-dlq")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
