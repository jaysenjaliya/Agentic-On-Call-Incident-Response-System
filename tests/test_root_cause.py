"""Tests for the root-cause subgraph (WI-17..21), nodes in isolation + graph."""

from __future__ import annotations

from agents.root_cause import (
    RootCauseResult,
    analyze_root_cause,
    build_root_cause_graph,
    check_deployments,
    search_runbooks,
)
from state import create_initial_state
from tests._fakes import StubLLM
from tools import FailureMode, MockGitHubAPI, MockRunbookSearch

ALERT = {"incident_id": "INC-001", "service_name": "checkout", "metric": "error_rate"}
NOOP = lambda *_: None  # noqa: E731


def _diagnosed_state():
    s = create_initial_state(ALERT)
    s["failing_component"] = "database connection pool"
    s["diagnosis_summary"] = "connection pool exhausted, psycopg2 operationalerror"
    s["logs"] = [{"level": "ERROR", "message": "connection pool exhausted"}]
    return s


class TestSearchRunbooks:
    def test_matches_rb101_for_checkout(self):
        u = search_runbooks(_diagnosed_state(), runbook_search=MockRunbookSearch(), sleep=NOOP)
        ids = [m["runbook_id"] for m in u["runbook_matches"]]
        assert "RB-101" in ids
        assert u["data_sources_succeeded"] == ["runbooks"]

    def test_no_match_returns_empty_usable(self):
        s = create_initial_state({"service_name": "x", "metric": "y"})
        s["diagnosis_summary"] = "quantum flux anomaly"
        u = search_runbooks(s, runbook_search=MockRunbookSearch(), sleep=NOOP)
        assert u["runbook_matches"] == []
        assert u["data_sources_succeeded"] == ["runbooks"]

    def test_failure_degrades(self):
        u = search_runbooks(_diagnosed_state(), runbook_search=MockRunbookSearch(FailureMode.TIMEOUT), sleep=NOOP)
        assert "runbook_matches" not in u
        assert u["data_sources_failed"] == ["runbooks"]


class TestCheckDeployments:
    def test_finds_suspect_deploy(self):
        u = check_deployments(_diagnosed_state(), github_api=MockGitHubAPI(), sleep=NOOP)
        assert u["regression_deployment"] is not None
        assert u["regression_deployment"]["suspect"] is True

    def test_failure_degrades(self):
        u = check_deployments(_diagnosed_state(), github_api=MockGitHubAPI(FailureMode.AUTH), sleep=NOOP)
        assert "deployments" not in u
        assert u["data_sources_failed"] == ["deployments"]


class TestAnalyzeRootCause:
    def test_high_confidence_with_runbook_and_deploy(self):
        s = _diagnosed_state()
        s["runbook_matches"] = [{"runbook_id": "RB-101", "title": "DB pool", "root_cause": "pool", "score": 3}]
        s["regression_deployment"] = {"sha": "a1b2c3d", "summary": "reduced pool"}
        llm = StubLLM(RootCauseResult(hypothesis="pool too small", confidence=0.92, matched_runbook_id="RB-101"))
        u = analyze_root_cause(s, llm=llm)
        assert u["root_cause_confidence"] == 0.92
        assert u["matched_runbook_id"] == "RB-101"
        assert u["current_phase"] == "remediation"
        assert u["audit_trail"][0]["confidence"] == 0.92

    def test_confidence_clamped(self):
        s = _diagnosed_state()
        llm = StubLLM(RootCauseResult(hypothesis="x", confidence=1.7, matched_runbook_id=None))
        u = analyze_root_cause(s, llm=llm)
        assert u["root_cause_confidence"] == 1.0

    def test_invalid_runbook_id_falls_back_to_top_match(self):
        s = _diagnosed_state()
        s["runbook_matches"] = [{"runbook_id": "RB-101"}]
        llm = StubLLM(RootCauseResult(hypothesis="x", confidence=0.9, matched_runbook_id="RB-999"))
        u = analyze_root_cause(s, llm=llm)
        assert u["matched_runbook_id"] == "RB-101"

    def test_llm_error_zero_confidence(self):
        u = analyze_root_cause(_diagnosed_state(), llm=StubLLM(raise_exc=RuntimeError("down")))
        assert u["root_cause_confidence"] == 0.0


class TestCompiledGraph:
    def test_full_run_audit_completeness(self):
        llm = StubLLM(RootCauseResult(hypothesis="pool exhausted", confidence=0.9, matched_runbook_id="RB-101"))
        g = build_root_cause_graph(llm=llm, sleep=NOOP)
        out = g.invoke(_diagnosed_state())
        assert out["root_cause_confidence"] == 0.9
        assert out["matched_runbook_id"] == "RB-101"
        assert [e["node_name"] for e in out["audit_trail"]] == [
            "search_runbooks", "check_deployments", "analyze_root_cause",
        ]
