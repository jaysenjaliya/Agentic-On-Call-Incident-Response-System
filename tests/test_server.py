"""Tests for the FastAPI deployment layer (server/app.py).

Offline & deterministic: the app is built with a graph_factory serving
PhaseStubLLM + mock tools (memory checkpointer, no-op sleeps), so no network or
API keys are needed. Runtime dirs are redirected to tmp; RUN_MODE is forced to
mock so no test can ever send a real notification.
"""

from __future__ import annotations

import time
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import config
from agents.supervisor import build_supervisor_graph
from server import create_app
from tests._fakes import PhaseStubLLM

NOOP = lambda *_: None  # noqa: E731
ALERT = {"incident_id": "INC-API", "service_name": "checkout",
         "metric": "error_rate", "threshold_violation": "34% > 5%"}
TERMINAL = ("completed", "paused_human_review", "error")


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Redirect all writes to tmp, force mock notifications, clear the API key."""
    monkeypatch.setattr(config, "AUDIT_TRAIL_DIR", tmp_path / "audit")
    monkeypatch.setattr(config, "DLQ_DIR", tmp_path / "dlq")
    monkeypatch.setattr(config, "INCIDENTS_DIR", tmp_path / "incidents")
    monkeypatch.setattr(config, "CHECKPOINT_DB", tmp_path / "cp" / "cp.sqlite")
    monkeypatch.setattr(config, "RUN_MODE", "mock")
    monkeypatch.setattr(config, "GMAIL_MCP_ENABLED", False)
    monkeypatch.delenv("SERVER_API_KEY", raising=False)
    return tmp_path


@contextmanager
def _client(confidence=0.92, severity="P1"):
    """A TestClient over an app whose graph uses the offline stub LLM.

    The factory accepts tool overrides so per-incident failure injection is
    exercised exactly as it is in production.
    """
    def factory(**tool_overrides):
        return build_supervisor_graph(
            llm=PhaseStubLLM(severity=severity, confidence=confidence), sleep=NOOP,
            **tool_overrides)
    with TestClient(create_app(graph_factory=factory)) as client:
        yield client


def _wait(client, incident_id, timeout=15.0):
    """Poll until the incident leaves 'running' (background thread finished)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = client.get(f"/incidents/{incident_id}").json()
        if record["status"] in TERMINAL:
            return record
        time.sleep(0.05)
    pytest.fail(f"incident {incident_id} still running after {timeout}s")


class TestHealthAndValidation:
    def test_health_ok(self):
        with _client() as c:
            body = c.get("/health").json()
        assert body["status"] == "ok"
        assert body["llm_provider"] == config.LLM_PROVIDER
        assert body["auth"] == "open"

    def test_missing_service_name_rejected(self):
        with _client() as c:
            assert c.post("/incidents", json={"metric": "error_rate"}).status_code == 422

    def test_unknown_incident_404(self):
        with _client() as c:
            assert c.get("/incidents/INC-NOPE").status_code == 404
            assert c.get("/incidents/INC-NOPE/audit").status_code == 404
            r = c.post("/incidents/INC-NOPE/hitl", json={"decision": "approve"})
            assert r.status_code == 404


class TestPipelineOverHttp:
    def test_high_confidence_auto_resolves(self):
        with _client(confidence=0.92) as c:
            r = c.post("/incidents", json=ALERT)
            assert r.status_code == 202
            assert r.json()["incident_id"] == "INC-API"
            record = _wait(c, "INC-API")
            assert record["status"] == "completed"
            assert record["resolution"] == config.RESOLUTION_RESOLVED
            assert record["total_steps"] > 0
            audit = c.get("/incidents/INC-API/audit").json()
            assert audit["source"] == "file"
            assert audit["events"][-1]["node_name"] == "finalize"

    def test_mid_confidence_pauses_then_approve_resolves(self):
        with _client(confidence=0.70) as c:
            c.post("/incidents", json=ALERT)
            record = _wait(c, "INC-API")
            assert record["status"] == "paused_human_review"
            # Paused runs expose their trail from the checkpoint, not a file.
            assert c.get("/incidents/INC-API/audit").json()["source"] == "checkpoint"
            r = c.post("/incidents/INC-API/hitl", json={"decision": "approve"})
            assert r.status_code == 202
            record = _wait(c, "INC-API")
            assert record["status"] == "completed"
            assert record["resolution"] == config.RESOLUTION_RESOLVED

    def test_mid_confidence_reject_escalates(self):
        with _client(confidence=0.70) as c:
            c.post("/incidents", json=ALERT)
            _wait(c, "INC-API")
            c.post("/incidents/INC-API/hitl", json={"decision": "reject"})
            record = _wait(c, "INC-API")
            assert record["resolution"] == config.RESOLUTION_ESCALATED

    def test_duplicate_submit_conflicts_while_active(self):
        with _client(confidence=0.70) as c:
            c.post("/incidents", json=ALERT)
            _wait(c, "INC-API")  # now paused_human_review — still active
            assert c.post("/incidents", json=ALERT).status_code == 409

    def test_hitl_on_completed_run_conflicts(self):
        with _client(confidence=0.92) as c:
            c.post("/incidents", json=ALERT)
            _wait(c, "INC-API")
            r = c.post("/incidents/INC-API/hitl", json={"decision": "approve"})
            assert r.status_code == 409

    def test_list_and_dlq_endpoints(self):
        with _client() as c:
            c.post("/incidents", json=ALERT)
            _wait(c, "INC-API")
            listed = c.get("/incidents").json()
            assert any(r["incident_id"] == "INC-API" for r in listed)
            assert c.get("/dlq").json() == []


class TestFailureInjection:
    """Per-request chaos switch — the live equivalent of the eval's inject_failures."""

    def test_all_data_sources_failing_escalates(self):
        with _client(confidence=0.92) as c:
            alert = dict(ALERT, inject_failures={"logs": "timeout", "metrics": "timeout"})
            r = c.post("/incidents", json=alert)
            assert r.status_code == 202
            assert r.json()["injected_failures"] == {"logs": "timeout", "metrics": "timeout"}
            record = _wait(c, "INC-API")
            # Both diagnosis data sources dead -> no partial data -> safe escalation.
            assert record["status"] == "completed"
            assert record["resolution"] == config.RESOLUTION_ESCALATED
            assert set(record["data_sources_failed"]) == {"logs", "metrics"}

    def test_partial_failure_degrades_gracefully(self):
        """One source down, one up -> the run still completes (NFR-4)."""
        with _client(confidence=0.92) as c:
            alert = dict(ALERT, inject_failures={"logs": "timeout"})
            c.post("/incidents", json=alert)
            record = _wait(c, "INC-API")
            assert record["status"] == "completed"
            assert record["resolution"] == config.RESOLUTION_RESOLVED
            assert record["data_sources_failed"] == ["logs"]

    def test_healthy_run_reports_no_failed_sources(self):
        with _client(confidence=0.92) as c:
            c.post("/incidents", json=ALERT)
            record = _wait(c, "INC-API")
            assert record["data_sources_failed"] == []
            assert record.get("injected_failures") is None

    @pytest.mark.parametrize("bad", [
        {"logs": "not_a_mode"},
        {"not_a_source": "timeout"},
    ])
    def test_invalid_injection_rejected(self, bad):
        with _client() as c:
            r = c.post("/incidents", json=dict(ALERT, inject_failures=bad))
            assert r.status_code == 422


class TestRootRedirect:
    def test_root_redirects_to_docs(self):
        with _client() as c:
            r = c.get("/", follow_redirects=False)
            assert r.status_code in (307, 302)
            assert r.headers["location"] == "/docs"


class TestApiKeyGate:
    def test_key_required_when_configured(self, monkeypatch):
        monkeypatch.setenv("SERVER_API_KEY", "test-key-123")
        with _client() as c:
            assert c.get("/health").status_code == 401
            ok = c.get("/health", headers={"X-API-Key": "test-key-123"})
            assert ok.status_code == 200
            assert ok.json()["auth"] == "api-key"
