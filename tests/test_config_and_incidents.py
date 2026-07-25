"""Sanity tests for config thresholds (WI-09) and seed incidents (WI-10)."""

from __future__ import annotations

import json

import config
from state import create_initial_state


class TestConfig:
    def test_prd_thresholds(self) -> None:
        # Values mandated by the PRD (FR-4, FR-5, NFR-3).
        assert config.MAX_RETRIES_PER_TOOL == 3
        assert config.MAX_TOTAL_STEPS == 20
        assert config.AUTO_FIX_THRESHOLD == 0.85
        assert config.HITL_LOWER_THRESHOLD == 0.50

    def test_gates_ordered(self) -> None:
        assert 0.0 < config.HITL_LOWER_THRESHOLD < config.AUTO_FIX_THRESHOLD < 1.0

    def test_p0_never_auto_resolves(self) -> None:
        assert "P0" in config.NO_AUTO_RESOLVE_SEVERITIES

    def test_taxonomies_are_complete(self) -> None:
        assert set(config.FAILURE_TYPES) == {"timeout", "rate_limit", "auth", "malformed", "unknown"}
        assert set(config.RESOLUTION_STATES) == {"resolved", "escalated", "dead_lettered"}
        assert config.SEVERITY_LEVELS == ("P0", "P1", "P2", "P3")

    def test_backoff_has_max_retries_entries(self) -> None:
        assert len(config.RETRY_BACKOFF_SECONDS) >= config.MAX_RETRIES_PER_TOOL


class TestSeedIncidents:
    REQUIRED = {"incident_id", "service_name", "metric", "threshold_violation", "timestamp"}

    def test_three_seed_incidents_exist(self) -> None:
        files = sorted(config.INCIDENTS_DIR.glob("incident_*.json"))
        assert len(files) >= 3

    def test_each_incident_valid_and_initializes_state(self) -> None:
        for path in sorted(config.INCIDENTS_DIR.glob("incident_*.json")):
            alert = json.loads(path.read_text(encoding="utf-8"))
            assert self.REQUIRED <= set(alert.keys()), f"{path.name} missing required fields"
            state = create_initial_state(alert)
            assert state["incident_id"] == alert["incident_id"]

    def test_expected_outcomes_cover_resolve_and_escalate(self) -> None:
        outcomes = set()
        for path in sorted(config.INCIDENTS_DIR.glob("incident_*.json")):
            alert = json.loads(path.read_text(encoding="utf-8"))
            outcomes.add(alert.get("expected_outcome"))
        assert "resolved" in outcomes
        assert "escalated" in outcomes
