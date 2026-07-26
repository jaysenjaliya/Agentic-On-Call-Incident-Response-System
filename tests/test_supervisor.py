"""End-to-end tests for the supervisor pipeline (WI-28..33).

Offline & deterministic: PhaseStubLLM drives routing, tools are mocks, sleeps are
no-ops. Runtime dirs are redirected to tmp so tests never touch the repo's data/.
"""

from __future__ import annotations

import json

import pytest

import config
from agents.supervisor import build_supervisor_graph
from state import create_initial_state
from tests._fakes import PhaseStubLLM
from tools import FailureMode, MockLogAPI, MockMetricsAPI, MockNotificationService

NOOP = lambda *_: None  # noqa: E731
ALERT = {"incident_id": "INC-T", "service_name": "checkout",
         "metric": "error_rate", "threshold_violation": "34% > 5%"}


@pytest.fixture(autouse=True)
def _redirect_dirs(monkeypatch, tmp_path):
    """Send audit-trail and DLQ writes to a temp dir for every test here."""
    monkeypatch.setattr(config, "AUDIT_TRAIL_DIR", tmp_path / "audit")
    monkeypatch.setattr(config, "DLQ_DIR", tmp_path / "dlq")
    return tmp_path


def _run(graph, state, thread="t", hitl=None):
    cfg = {"configurable": {"thread_id": thread}}
    out = graph.invoke(state, cfg)
    if graph.get_state(cfg).next == ("human_review",):
        if hitl is None:
            return graph, cfg, out  # leave paused
        graph.update_state(cfg, {"human_decision": hitl})
        out = graph.invoke(None, cfg)
    return graph, cfg, out


def _graph(**overrides):
    overrides.setdefault("sleep", NOOP)
    return build_supervisor_graph(**overrides)


class TestHappyPath:
    def test_auto_resolve_full_pipeline(self):
        g = _graph(llm=PhaseStubLLM(severity="P1", confidence=0.92))
        _, _, out = _run(g, create_initial_state(ALERT), "resolve")
        assert out["resolution"] == config.RESOLUTION_RESOLVED
        assert out["fix_verified"] is True
        # Audit completeness: every executed node logged, ending at finalize.
        nodes = [e["node_name"] for e in out["audit_trail"]]
        assert nodes == [
            "pull_logs", "pull_metrics", "analyze_diagnosis", "search_runbooks",
            "check_deployments", "analyze_root_cause", "evaluate_confidence",
            "execute_fix", "verify_fix", "close_incident", "finalize",
        ]

    def test_finalize_writes_audit_file(self):
        g = _graph(llm=PhaseStubLLM())
        _, _, out = _run(g, create_initial_state(ALERT), "auditfile")
        audit_file = config.AUDIT_TRAIL_DIR / "INC-T_audit.json"
        assert audit_file.exists()
        data = json.loads(audit_file.read_text(encoding="utf-8"))
        assert data["events"][-1]["node_name"] == "finalize"


class TestEscalation:
    def test_low_confidence_escalates(self):
        notifier = MockNotificationService()
        g = _graph(llm=PhaseStubLLM(severity="P2", confidence=0.30), notifier=notifier)
        _, _, out = _run(g, create_initial_state(ALERT), "esc")
        assert out["resolution"] == config.RESOLUTION_ESCALATED
        assert len(notifier.sent) == 1

    def test_p0_escalates_regardless_of_confidence(self):
        g = _graph(llm=PhaseStubLLM(severity="P0", confidence=0.99))
        _, _, out = _run(g, create_initial_state(ALERT), "p0")
        assert out["resolution"] == config.RESOLUTION_ESCALATED


class TestKillSwitch:
    def test_exceeding_max_steps_dead_letters(self, monkeypatch):
        monkeypatch.setattr(config, "MAX_TOTAL_STEPS", 3)
        g = _graph(llm=PhaseStubLLM())
        _, _, out = _run(g, create_initial_state(ALERT), "kill")
        assert out["resolution"] == config.RESOLUTION_DEAD_LETTERED
        assert out["dead_lettered"] is True
        assert "dead_letter" in [e["node_name"] for e in out["audit_trail"]]

    def test_dead_letter_writes_dlq_file(self, monkeypatch):
        monkeypatch.setattr(config, "MAX_TOTAL_STEPS", 3)
        g = _graph(llm=PhaseStubLLM())
        _, _, out = _run(g, create_initial_state(ALERT), "killfile")
        assert (config.DLQ_DIR / "INC-T_dlq.json").exists()
        assert out["dlq_reference"]


class TestFailureResilience:
    def test_single_tool_failure_does_not_crash(self):
        # Logs time out, metrics succeed -> pipeline still resolves (degradation).
        g = _graph(
            llm=PhaseStubLLM(severity="P1", confidence=0.92),
            log_api=MockLogAPI(FailureMode.TIMEOUT),
        )
        _, _, out = _run(g, create_initial_state(ALERT), "degrade")
        assert out["resolution"] == config.RESOLUTION_RESOLVED
        assert "logs" in out["data_sources_failed"]
        assert "metrics" in out["data_sources_succeeded"]

    def test_all_data_sources_fail_escalates(self):
        g = _graph(
            llm=PhaseStubLLM(),
            log_api=MockLogAPI(FailureMode.TIMEOUT),
            metrics_api=MockMetricsAPI(FailureMode.TIMEOUT),
        )
        _, _, out = _run(g, create_initial_state(ALERT), "allfail")
        assert out["resolution"] == config.RESOLUTION_ESCALATED
        nodes = [e["node_name"] for e in out["audit_trail"]]
        assert "handle_diagnosis_failure" in nodes


class TestHITL:
    def test_mid_confidence_pauses_then_approve_resolves(self):
        g = _graph(llm=PhaseStubLLM(severity="P1", confidence=0.70))
        g, cfg, _ = _run(g, create_initial_state(ALERT), "hitl-a")  # leaves paused
        assert g.get_state(cfg).next == ("human_review",)
        g.update_state(cfg, {"human_decision": "approve"})
        out = g.invoke(None, cfg)
        assert out["resolution"] == config.RESOLUTION_RESOLVED

    def test_mid_confidence_reject_escalates(self):
        g = _graph(llm=PhaseStubLLM(severity="P1", confidence=0.70))
        _, _, out = _run(g, create_initial_state(ALERT), "hitl-r", hitl="reject")
        assert out["resolution"] == config.RESOLUTION_ESCALATED


class TestCrashRecovery:
    def test_sqlite_checkpoint_resumes_after_new_graph(self, tmp_path):
        """A fresh graph object with the same SQLite db + thread resumes the run."""
        from agents.supervisor import make_sqlite_checkpointer

        db = tmp_path / "cp.sqlite"
        cfg = {"configurable": {"thread_id": "recover"}}
        # First graph pauses at HITL, persisting state to SQLite.
        g1 = build_supervisor_graph(
            llm=PhaseStubLLM(severity="P1", confidence=0.70),
            checkpointer=make_sqlite_checkpointer(db), sleep=NOOP,
        )
        g1.invoke(create_initial_state(ALERT), cfg)
        assert g1.get_state(cfg).next == ("human_review",)
        # A brand-new graph object, same db + thread, resumes and finishes.
        g2 = build_supervisor_graph(
            llm=PhaseStubLLM(severity="P1", confidence=0.70),
            checkpointer=make_sqlite_checkpointer(db), sleep=NOOP,
        )
        g2.update_state(cfg, {"human_decision": "approve"})
        out = g2.invoke(None, cfg)
        assert out["resolution"] == config.RESOLUTION_RESOLVED
