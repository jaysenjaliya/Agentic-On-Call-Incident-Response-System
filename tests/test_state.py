"""Unit tests for the state schema and factory (WI-01)."""

from __future__ import annotations

import config
from state import AuditEvent, DeadLetterEntry, IncidentState, create_initial_state

SAMPLE_ALERT = {
    "incident_id": "INC-001",
    "service_name": "checkout",
    "metric": "error_rate",
    "threshold_violation": ">5%",
    "timestamp": "2026-07-25T02:00:00Z",
}


class TestCreateInitialState:
    def test_all_schema_fields_present(self) -> None:
        state = create_initial_state(SAMPLE_ALERT)
        assert set(state.keys()) == set(IncidentState.__annotations__.keys())

    def test_input_fields_from_alert(self) -> None:
        state = create_initial_state(SAMPLE_ALERT)
        assert state["incident_id"] == "INC-001"
        assert state["service_name"] == "checkout"
        assert state["metric"] == "error_rate"
        assert state["raw_alert"] == SAMPLE_ALERT

    def test_defaults(self) -> None:
        state = create_initial_state(SAMPLE_ALERT)
        assert state["severity"] == config.DEFAULT_SEVERITY
        assert state["root_cause_confidence"] == 0.0
        assert state["resolution"] == ""
        assert state["total_steps"] == 0
        assert state["retry_count"] == 0
        assert state["tool_retry_counts"] == {}
        assert state["current_phase"] == "diagnosis"
        assert state["needs_human_review"] is False
        assert state["should_escalate"] is False
        assert state["is_terminated"] is False
        assert state["audit_trail"] == []
        assert state["dead_lettered"] is False
        assert state["logs"] is None
        assert state["metrics"] is None

    def test_generates_id_when_missing(self) -> None:
        state = create_initial_state({"service_name": "x", "metric": "m", "threshold_violation": "t"})
        assert state["incident_id"].startswith("INC-")

    def test_accepts_id_alias(self) -> None:
        state = create_initial_state({"id": "ABC-9", "service_name": "x"})
        assert state["incident_id"] == "ABC-9"

    def test_mutating_returned_state_does_not_touch_defaults(self) -> None:
        # Each call must produce independent mutable containers.
        s1 = create_initial_state(SAMPLE_ALERT)
        s1["audit_trail"].append(AuditEvent(node_name="n", action="a"))
        s2 = create_initial_state(SAMPLE_ALERT)
        assert s2["audit_trail"] == []


class TestPydanticModels:
    def test_audit_event_defaults_timestamp(self) -> None:
        event = AuditEvent(node_name="pull_logs", action="fetched logs")
        assert event.timestamp
        assert event.confidence is None and event.error is None

    def test_audit_event_roundtrip(self) -> None:
        event = AuditEvent(node_name="n", action="a", confidence=0.9)
        assert AuditEvent.model_validate(event.model_dump()) == event

    def test_dead_letter_entry_roundtrip(self) -> None:
        entry = DeadLetterEntry(incident_id="INC-1", reason="max_steps_exceeded", total_steps=21)
        assert DeadLetterEntry.model_validate(entry.model_dump()) == entry
