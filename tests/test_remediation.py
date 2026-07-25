"""Tests for the remediation subgraph (WI-22..27): 3-branch routing + HITL."""

from __future__ import annotations

import config
from agents.remediation import (
    build_remediation_graph,
    close_incident,
    escalate,
    evaluate_confidence,
    execute_fix,
    human_review,
    route_by_confidence,
    verify_fix,
)
from state import create_initial_state
from tools import FailureMode, MockNotificationService

RUNBOOK = {"runbook_id": "RB-101", "title": "DB pool",
           "remediation_steps": ["Increase pool size", "Recycle connections"]}


def _state(confidence: float, severity: str):
    s = create_initial_state({"incident_id": "INC", "service_name": "checkout", "metric": "error_rate"})
    s["root_cause_confidence"] = confidence
    s["severity"] = severity
    s["matched_runbook_id"] = "RB-101"
    s["runbook_matches"] = [RUNBOOK]
    return s


class TestEvaluateConfidence:
    def test_high_confidence_auto_fix(self):
        u = evaluate_confidence(_state(0.92, "P1"))
        assert u["next_action"] == "auto_fix"

    def test_mid_confidence_human_review(self):
        u = evaluate_confidence(_state(0.70, "P1"))
        assert u["next_action"] == "human_review"
        assert u["needs_human_review"] is True

    def test_low_confidence_escalate(self):
        u = evaluate_confidence(_state(0.30, "P2"))
        assert u["next_action"] == "escalate"
        assert u["should_escalate"] is True

    def test_p0_never_auto_resolves_even_high_confidence(self):
        u = evaluate_confidence(_state(0.99, "P0"))
        assert u["next_action"] == "escalate"

    def test_boundary_085_is_human_review(self):
        # confidence == AUTO_FIX_THRESHOLD is NOT > threshold -> human review.
        u = evaluate_confidence(_state(config.AUTO_FIX_THRESHOLD, "P1"))
        assert u["next_action"] == "human_review"

    def test_routing_maps_action_to_node(self):
        assert route_by_confidence({"next_action": "auto_fix"}) == "execute_fix"
        assert route_by_confidence({"next_action": "human_review"}) == "human_review"
        assert route_by_confidence({"next_action": "escalate"}) == "escalate"


class TestFixNodes:
    def test_execute_fix_applies_runbook_steps(self):
        u = execute_fix(_state(0.9, "P1"))
        assert u["fix_applied"] is True
        assert u["remediation_steps"] == RUNBOOK["remediation_steps"]
        assert "RB-101" in u["remediation_action"]

    def test_execute_fix_without_runbook_uses_generic(self):
        s = _state(0.9, "P1"); s["matched_runbook_id"] = None; s["runbook_matches"] = []
        u = execute_fix(s)
        assert u["fix_applied"] is True
        assert u["remediation_steps"] == []

    def test_verify_fix_success(self):
        s = _state(0.9, "P1"); s["fix_applied"] = True
        assert verify_fix(s)["fix_verified"] is True

    def test_verify_fix_failure_when_not_applied(self):
        s = _state(0.9, "P1"); s["fix_applied"] = False
        assert verify_fix(s)["fix_verified"] is False


class TestHumanReview:
    def test_approve_routes_to_auto_fix(self):
        s = _state(0.7, "P1"); s["human_decision"] = "approve"
        assert human_review(s)["next_action"] == "auto_fix"

    def test_reject_routes_to_escalate(self):
        s = _state(0.7, "P1"); s["human_decision"] = "reject"
        u = human_review(s)
        assert u["next_action"] == "escalate"
        assert u["should_escalate"] is True

    def test_no_decision_fails_safe_to_escalate(self):
        assert human_review(_state(0.7, "P1"))["next_action"] == "escalate"


class TestTerminalNodes:
    def test_close_incident_resolves(self):
        assert close_incident(_state(0.9, "P1"))["resolution"] == config.RESOLUTION_RESOLVED

    def test_escalate_sends_notification(self):
        notifier = MockNotificationService()
        u = escalate(_state(0.3, "P2"), notifier=notifier)
        assert u["resolution"] == config.RESOLUTION_ESCALATED
        assert len(notifier.sent) == 1

    def test_escalate_survives_notification_failure(self):
        notifier = MockNotificationService(FailureMode.TIMEOUT)
        u = escalate(_state(0.3, "P2"), notifier=notifier)
        # Incident still terminates cleanly even though notify failed.
        assert u["resolution"] == config.RESOLUTION_ESCALATED
        assert u["audit_trail"][0]["error"] is not None


class TestCompiledGraph:
    """Full three-branch routing + HITL pause/resume via the compiled graph."""

    def _run(self, s, thread):
        g = build_remediation_graph()
        cfg = {"configurable": {"thread_id": thread}}
        out = g.invoke(s, cfg)
        return g, cfg, out

    def test_auto_fix_branch_resolves(self):
        _, _, out = self._run(_state(0.92, "P1"), "auto")
        assert out["resolution"] == config.RESOLUTION_RESOLVED
        assert out["fix_verified"] is True

    def test_low_confidence_escalates(self):
        _, _, out = self._run(_state(0.30, "P2"), "esc")
        assert out["resolution"] == config.RESOLUTION_ESCALATED

    def test_p0_escalates(self):
        _, _, out = self._run(_state(0.99, "P0"), "p0")
        assert out["resolution"] == config.RESOLUTION_ESCALATED

    def test_hitl_pauses_then_approve_resolves(self):
        g, cfg, _ = self._run(_state(0.70, "P1"), "hitl-approve")
        # Paused before human_review (interrupt_before), not yet terminal.
        assert g.get_state(cfg).next == ("human_review",)
        g.update_state(cfg, {"human_decision": "approve"})
        out = g.invoke(None, cfg)
        assert out["resolution"] == config.RESOLUTION_RESOLVED

    def test_hitl_pauses_then_reject_escalates(self):
        g, cfg, _ = self._run(_state(0.70, "P1"), "hitl-reject")
        g.update_state(cfg, {"human_decision": "reject"})
        out = g.invoke(None, cfg)
        assert out["resolution"] == config.RESOLUTION_ESCALATED
