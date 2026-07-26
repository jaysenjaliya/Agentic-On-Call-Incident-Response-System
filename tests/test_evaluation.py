"""Tests for the evaluation harness and metrics (WI-35, WI-36).

The metrics math is tested with synthetic result records (no LLM). One offline
end-to-end harness test uses a PhaseStubLLM to confirm run_one wiring + injected
failures + the smart-HITL policy.
"""

from __future__ import annotations

from evaluation.metrics import compute_metrics, format_metrics_table


def _result(iid, category, expected, actual, *, steps=11, events=None,
            dead=False, confidence=0.9):
    return {
        "incident_id": iid, "service": "svc", "category": category,
        "expected_outcome": expected, "actual_outcome": actual,
        "severity": "P1", "confidence": confidence, "steps": steps,
        "audit_events": steps if events is None else events,
        "data_sources_failed": [], "injected_failures": {},
        "hitl_fired": False, "hitl_decision": None, "dead_lettered": dead,
        "notifications_sent": 0, "matched_runbook": None,
    }


def _perfect_suite():
    # 10 resolve, 5 escalate, 5 tool-failure (4 resolve + 1 escalate), all correct.
    rs = [_result(f"R{i}", "auto_resolve", "resolved", "resolved") for i in range(10)]
    es = [_result(f"E{i}", "escalation", "escalated", "escalated", steps=9) for i in range(5)]
    tf = [_result(f"T{i}", "tool_failure", "resolved", "resolved") for i in range(4)]
    tf.append(_result("T4", "tool_failure", "escalated", "escalated", steps=9))
    return rs + es + tf


class TestMetricsMath:
    def test_perfect_suite_all_pass(self):
        m = compute_metrics(_perfect_suite())
        assert m["resolution_rate"]["value"] == 1.0
        assert m["escalation_precision"]["value"] == 1.0
        assert m["escalation_recall"]["value"] == 1.0
        assert m["failure_recovery_rate"]["value"] == 1.0
        assert m["audit_completeness"]["value"] == 1.0
        assert all(m[k]["pass"] for k in (
            "resolution_rate", "escalation_precision", "escalation_recall",
            "failure_recovery_rate", "audit_completeness", "avg_steps_to_resolution",
        ))

    def test_resolution_rate_counts_only_resolvable(self):
        suite = _perfect_suite()
        # Flip one auto-resolve to escalated -> 13/14 resolvable resolved.
        suite[0]["actual_outcome"] = "escalated"
        m = compute_metrics(suite)
        assert m["resolution_rate"]["value"] == round(13 / 14, 4)

    def test_precision_penalises_wrong_escalation(self):
        suite = _perfect_suite()
        suite[0]["actual_outcome"] = "escalated"  # a resolvable incident wrongly escalated
        m = compute_metrics(suite)
        # 6 correct escalations / 7 total escalations.
        assert m["escalation_precision"]["value"] == round(6 / 7, 4)

    def test_recall_penalises_missed_escalation(self):
        suite = _perfect_suite()
        suite[10]["actual_outcome"] = "resolved"  # an escalation-needed incident resolved
        m = compute_metrics(suite)
        assert m["escalation_recall"]["value"] == round(5 / 6, 4)  # 5 caught of 6 needed

    def test_audit_incompleteness_detected(self):
        suite = _perfect_suite()
        suite[0]["audit_events"] = suite[0]["steps"] - 1  # a node skipped logging
        m = compute_metrics(suite)
        assert m["audit_completeness"]["value"] < 1.0
        assert m["audit_completeness"]["pass"] is False

    def test_dlq_capture_vacuous_when_none_unrecoverable(self):
        m = compute_metrics(_perfect_suite())
        # No incident is expected to dead-letter -> reported as 1.0 (0/0 n/a).
        assert m["dlq_capture_rate"]["pass"] is True

    def test_dlq_capture_counts_captured(self):
        suite = _perfect_suite()
        suite.append(_result("D0", "auto_resolve", "dead_lettered", "dead_lettered", dead=True))
        m = compute_metrics(suite)
        assert m["dlq_capture_rate"]["value"] == 1.0

    def test_table_renders(self):
        table = format_metrics_table(compute_metrics(_perfect_suite()))
        assert "Resolution rate" in table
        assert "PASS" in table


class TestHarnessOffline:
    def test_run_one_with_stub_and_injected_failure(self, monkeypatch):
        import config
        from evaluation.run_eval import run_one
        from tests._fakes import PhaseStubLLM

        monkeypatch.setattr(config, "RUN_MODE", "mock")
        # Patch get_llm used inside build_supervisor_graph to a deterministic stub.
        monkeypatch.setattr("agents.supervisor.get_llm",
                            lambda: PhaseStubLLM(severity="P1", confidence=0.92))
        alert = {"incident_id": "INC-T", "service_name": "checkout",
                 "metric": "error_rate", "threshold_violation": "34%",
                 "category": "tool_failure", "expected_outcome": "resolved",
                 "inject_failures": {"metrics": "timeout"}}
        r = run_one(alert)
        assert r["actual_outcome"] == "resolved"
        assert r["injected_failures"] == {"metrics": "timeout"}
        assert r["audit_events"] == r["steps"]  # audit completeness holds
