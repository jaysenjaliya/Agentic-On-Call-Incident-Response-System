"""Unit tests for the dead letter queue utility (WI-08)."""

from __future__ import annotations

import json
from pathlib import Path

from state import create_initial_state
from state.schemas import AuditEvent, DeadLetterEntry
from utils.dead_letter_queue import review_dlq, send_to_dlq

ALERT = {"incident_id": "INC-DLQ", "service_name": "checkout", "metric": "error_rate"}


def _failed_state():
    state = create_initial_state(ALERT)
    state["total_steps"] = 21
    state["last_failure_type"] = "timeout"
    state["last_error"] = "MockLogAPI timed out"
    state["audit_trail"] = [AuditEvent(node_name="pull_logs", action="tried", error="timeout")]
    return state


class TestSendToDlq:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        path = send_to_dlq(_failed_state(), reason="max_steps_exceeded", directory=tmp_path)
        assert path.exists()
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["incident_id"] == "INC-DLQ"
        assert raw["reason"] == "max_steps_exceeded"
        assert raw["failure_type"] == "timeout"
        assert raw["total_steps"] == 21

    def test_snapshot_serializes_audit_events(self, tmp_path: Path) -> None:
        path = send_to_dlq(_failed_state(), reason="all_data_sources_failed", directory=tmp_path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        trail = raw["state_snapshot"]["audit_trail"]
        assert len(trail) == 1
        assert trail[0]["node_name"] == "pull_logs"  # dumped to a plain dict, JSON-safe

    def test_explicit_failure_type_overrides_state(self, tmp_path: Path) -> None:
        path = send_to_dlq(_failed_state(), reason="x", failure_type="auth", directory=tmp_path)
        assert json.loads(path.read_text(encoding="utf-8"))["failure_type"] == "auth"


class TestReviewDlq:
    def test_roundtrip(self, tmp_path: Path) -> None:
        send_to_dlq(_failed_state(), reason="max_steps_exceeded", directory=tmp_path)
        entries = review_dlq(directory=tmp_path)
        assert len(entries) == 1
        assert isinstance(entries[0], DeadLetterEntry)
        assert entries[0].incident_id == "INC-DLQ"

    def test_empty_or_missing_dir_returns_empty_list(self, tmp_path: Path) -> None:
        assert review_dlq(directory=tmp_path) == []
        assert review_dlq(directory=tmp_path / "does-not-exist") == []

    def test_multiple_entries_sorted_newest_first(self, tmp_path: Path) -> None:
        s1 = _failed_state()
        s1["incident_id"] = "INC-A"
        e1 = send_to_dlq(s1, reason="r1", directory=tmp_path)
        s2 = _failed_state()
        s2["incident_id"] = "INC-B"
        send_to_dlq(s2, reason="r2", directory=tmp_path)
        # Force distinct, ordered timestamps regardless of write speed.
        raw = json.loads(e1.read_text(encoding="utf-8"))
        raw["timestamp"] = "2000-01-01T00:00:00+00:00"
        e1.write_text(json.dumps(raw), encoding="utf-8")
        entries = review_dlq(directory=tmp_path)
        assert [e.incident_id for e in entries] == ["INC-B", "INC-A"]
