"""Unit tests for the audit trail utility (WI-07)."""

from __future__ import annotations

import json
from pathlib import Path

from state.schemas import AuditEvent
from utils.audit_trail import append_audit_event, format_trail_for_human, save_trail_to_file


class TestAppendAuditEvent:
    def test_returns_audit_event_with_fields(self) -> None:
        event = append_audit_event(
            "pull_logs", "fetched logs", tool_used="MockLogAPI",
            output_summary="6 lines", confidence=0.8, step_number=1,
        )
        assert isinstance(event, AuditEvent)
        assert event.node_name == "pull_logs"
        assert event.tool_used == "MockLogAPI"
        assert event.confidence == 0.8
        assert event.step_number == 1

    def test_reducer_style_append(self) -> None:
        # Mirrors how a node appends: {"audit_trail": [event]} concatenated via reducer.
        trail: list[AuditEvent] = []
        trail = trail + [append_audit_event("a", "did a")]
        trail = trail + [append_audit_event("b", "did b")]
        assert [e.node_name for e in trail] == ["a", "b"]


class TestFormatTrail:
    def test_empty_trail(self) -> None:
        assert "empty" in format_trail_for_human([]).lower()

    def test_format_includes_details(self) -> None:
        trail = [
            append_audit_event("pull_logs", "fetched", tool_used="MockLogAPI", step_number=1),
            append_audit_event("analyze", "scored", decision="severity=P1", confidence=0.82, step_number=2),
        ]
        text = format_trail_for_human(trail)
        assert "pull_logs" in text
        assert "MockLogAPI" in text
        assert "severity=P1" in text
        assert "0.82" in text


class TestSaveTrail:
    def test_save_writes_json(self, tmp_path: Path) -> None:
        trail = [append_audit_event("pull_logs", "fetched", step_number=1)]
        path = save_trail_to_file(trail, "INC-XYZ", directory=tmp_path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["incident_id"] == "INC-XYZ"
        assert data["event_count"] == 1
        assert data["events"][0]["node_name"] == "pull_logs"

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "audit"
        path = save_trail_to_file([], "INC-EMPTY", directory=target)
        assert path.exists()
