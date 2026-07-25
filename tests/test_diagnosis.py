"""Tests for the diagnosis subgraph (WI-11..16), nodes in isolation + compiled graph.

All offline: tools are mocks, the LLM is a StubLLM. Retry sleeps are no-ops.
"""

from __future__ import annotations

import pytest

import config
from agents.diagnosis import (
    DiagnosisResult,
    analyze_diagnosis,
    build_diagnosis_graph,
    handle_diagnosis_failure,
    pull_logs,
    pull_metrics,
    route_after_data,
)
from state import create_initial_state
from tests._fakes import StubLLM
from tools import FailureMode, MockLogAPI, MockMetricsAPI

ALERT = {
    "incident_id": "INC-001", "service_name": "checkout",
    "metric": "error_rate", "threshold_violation": "34% > 5%",
}
NOOP = lambda *_: None  # noqa: E731 - test sleep stub
GOOD_DIAGNOSIS = DiagnosisResult(
    failing_component="DB pool", blast_radius="checkout users", severity="P1", summary="pool exhausted"
)


def _state():
    return create_initial_state(ALERT)


class TestPullLogs:
    def test_happy_path_sets_logs_and_one_audit(self):
        u = pull_logs(_state(), log_api=MockLogAPI(), sleep=NOOP)
        assert u["logs"]
        assert u["data_sources_succeeded"] == ["logs"]
        assert u["total_steps"] == 1
        assert len(u["audit_trail"]) == 1  # exactly one audit event

    @pytest.mark.parametrize("mode,expected", [
        (FailureMode.TIMEOUT, config.FAILURE_TIMEOUT),
        (FailureMode.RATE_LIMIT, config.FAILURE_RATE_LIMIT),
        (FailureMode.AUTH, config.FAILURE_AUTH),
    ])
    def test_failure_degrades_not_crashes(self, mode, expected):
        u = pull_logs(_state(), log_api=MockLogAPI(mode), sleep=NOOP)
        assert "logs" not in u  # no data written
        assert u["data_sources_failed"] == ["logs"]
        assert u["last_failure_type"] == expected
        assert len(u["audit_trail"]) == 1

    def test_empty_is_usable_not_a_failure(self):
        u = pull_logs(_state(), log_api=MockLogAPI(FailureMode.EMPTY), sleep=NOOP)
        assert u["logs"] == []                      # empty but present
        assert u["data_sources_succeeded"] == ["logs"]


class TestPullMetrics:
    def test_happy_path(self):
        u = pull_metrics(_state(), metrics_api=MockMetricsAPI(), sleep=NOOP)
        assert u["metrics"]["service"] == "checkout"
        assert u["data_sources_succeeded"] == ["metrics"]

    def test_failure_degrades(self):
        u = pull_metrics(_state(), metrics_api=MockMetricsAPI(FailureMode.TIMEOUT), sleep=NOOP)
        assert "metrics" not in u
        assert u["data_sources_failed"] == ["metrics"]


class TestRouting:
    def test_route_to_analyze_when_any_data(self):
        s = _state(); s["logs"] = [{"x": 1}]
        assert route_after_data(s) == "analyze_diagnosis"

    def test_route_to_failure_when_no_data(self):
        assert route_after_data(_state()) == "handle_diagnosis_failure"

    def test_partial_data_still_analyzes(self):
        # logs fail, metrics ok -> must still analyze (graceful degradation).
        s = _state()
        s.update(pull_logs(s, log_api=MockLogAPI(FailureMode.TIMEOUT), sleep=NOOP))
        s.update(pull_metrics(s, metrics_api=MockMetricsAPI(), sleep=NOOP))
        assert route_after_data(s) == "analyze_diagnosis"


class TestAnalyzeDiagnosis:
    def test_produces_structured_diagnosis(self):
        s = _state(); s["logs"] = [{"level": "ERROR", "message": "pool exhausted"}]
        u = analyze_diagnosis(s, llm=StubLLM(GOOD_DIAGNOSIS))
        assert u["severity"] == "P1"
        assert u["failing_component"] == "DB pool"
        assert u["diagnosis_summary"] == "pool exhausted"
        assert u["current_phase"] == "root_cause"

    def test_invalid_severity_falls_back_to_default(self):
        s = _state(); s["metrics"] = {"service": "checkout"}
        bad = DiagnosisResult(failing_component="x", blast_radius="y", severity="SEV1", summary="z")
        u = analyze_diagnosis(s, llm=StubLLM(bad))
        assert u["severity"] == config.DEFAULT_SEVERITY

    def test_llm_error_degrades_gracefully(self):
        s = _state(); s["logs"] = [{"level": "ERROR", "message": "x"}]
        u = analyze_diagnosis(s, llm=StubLLM(raise_exc=RuntimeError("model down")))
        assert u["severity"] == config.DEFAULT_SEVERITY
        assert "unavailable" in u["diagnosis_summary"]
        assert u["audit_trail"][0]["error"] is not None


class TestHandleFailure:
    def test_sets_escalation(self):
        s = _state(); s["data_sources_failed"] = ["logs", "metrics"]
        u = handle_diagnosis_failure(s)
        assert u["should_escalate"] is True
        assert u["next_action"] == "escalate"


class TestCompiledGraph:
    def test_full_run_normal(self):
        g = build_diagnosis_graph(llm=StubLLM(GOOD_DIAGNOSIS), sleep=NOOP)
        out = g.invoke(_state())
        assert out["severity"] == "P1"
        assert out["current_phase"] == "root_cause"
        # Audit completeness: one event per executed node, none missing.
        assert [e["node_name"] for e in out["audit_trail"]] == [
            "pull_logs", "pull_metrics", "analyze_diagnosis",
        ]

    def test_all_sources_fail_routes_to_escalation(self):
        g = build_diagnosis_graph(
            llm=StubLLM(GOOD_DIAGNOSIS),
            log_api=MockLogAPI(FailureMode.TIMEOUT),
            metrics_api=MockMetricsAPI(FailureMode.TIMEOUT),
            sleep=NOOP,
        )
        out = g.invoke(_state())
        assert out["should_escalate"] is True
        assert [e["node_name"] for e in out["audit_trail"]] == [
            "pull_logs", "pull_metrics", "handle_diagnosis_failure",
        ]
