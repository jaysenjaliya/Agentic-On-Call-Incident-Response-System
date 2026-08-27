"""FastAPI app serving the incident-response supervisor pipeline over HTTP.

Endpoints (all JSON):
    GET  /health                    liveness + provider/tracing status
    POST /incidents                 submit an alert; runs the pipeline in the
                                    background (202 + status URL)
    GET  /incidents                 list every incident this server has seen
    GET  /incidents/{id}            status/result of one incident
    POST /incidents/{id}/hitl       approve/reject a run paused at human_review
    GET  /incidents/{id}/audit      the incident's audit trail
    GET  /dlq                       dead letter queue contents

Design notes:
- The supervisor graph is built once at startup with the SQLite checkpointer,
  so runs survive a server restart (resume via the same thread_id) and the HITL
  interrupt pauses runs exactly as in the CLI.
- Incidents execute on a small thread pool; POST returns 202 immediately and
  clients poll GET /incidents/{id}. An in-memory registry tracks live status;
  for incidents from before a restart, status is reconstructed from the
  checkpoint database.
- If SERVER_API_KEY is set in the environment, every request must carry it in
  an ``X-API-Key`` header. Leave it unset for open LAN testing.
"""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

import config
from state import create_initial_state
from utils import review_dlq
from utils.observability import run_config, tracing_status

# Statuses a registry record can hold. "running" covers both the first pass and
# a post-HITL resume; terminal statuses mirror the graph's resolution contract.
Status = Literal["running", "paused_human_review", "completed", "error"]

_HITL_NEXT: tuple[str, ...] = ("human_review",)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class AlertIn(BaseModel):
    """An incoming alert. Extra fields are kept and passed through as raw_alert."""

    model_config = ConfigDict(extra="allow")

    incident_id: str | None = None
    service_name: str = Field(min_length=1)
    metric: str = ""
    threshold_violation: str = ""
    timestamp: str = ""


class HitlIn(BaseModel):
    """A human decision for a run paused at the human_review checkpoint."""

    decision: Literal["approve", "reject"]


# ---------------------------------------------------------------------------
# API-key gate (optional — active only when SERVER_API_KEY is set)
# ---------------------------------------------------------------------------
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Reject the request when SERVER_API_KEY is set and the header mismatches."""
    expected = os.getenv("SERVER_API_KEY", "")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key header")


# ---------------------------------------------------------------------------
# Shared runtime state
# ---------------------------------------------------------------------------
class _Runtime:
    """Holds the compiled graph, the worker pool, and the incident registry."""

    def __init__(self, graph: Any) -> None:
        self.graph = graph
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="incident")
        self.registry: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def update(self, incident_id: str, **fields: Any) -> None:
        with self.lock:
            self.registry.setdefault(incident_id, {"incident_id": incident_id}).update(fields)

    def get(self, incident_id: str) -> dict[str, Any] | None:
        with self.lock:
            record = self.registry.get(incident_id)
            return dict(record) if record else None


def _summarize(out: dict[str, Any]) -> dict[str, Any]:
    """Extract the client-facing summary fields from a (possibly partial) state."""
    return {
        "severity": out.get("severity"),
        "root_cause_hypothesis": out.get("root_cause_hypothesis") or None,
        "root_cause_confidence": out.get("root_cause_confidence"),
        "resolution": out.get("resolution") or None,
        "total_steps": out.get("total_steps"),
        "dlq_reference": out.get("dlq_reference"),
    }


def _execute(rt: _Runtime, incident_id: str, state: Any = None,
             decision: str | None = None) -> None:
    """Worker: run (or resume) one incident through the graph and record the outcome.

    ``state`` set -> fresh run from an initial state; ``decision`` set -> resume a
    HITL-paused run with that human decision. Ends the registry record in
    completed / paused_human_review / error.
    """
    cfg = run_config(incident_id, thread_id=incident_id)
    try:
        if decision is not None:
            rt.graph.update_state(cfg, {"human_decision": decision})
        out = rt.graph.invoke(state, cfg)
        if rt.graph.get_state(cfg).next == _HITL_NEXT:
            rt.update(incident_id, status="paused_human_review", **_summarize(out))
        else:
            rt.update(incident_id, status="completed", **_summarize(out))
    except Exception as exc:  # noqa: BLE001 - surfaced to the client, never dropped
        rt.update(incident_id, status="error", error=f"{type(exc).__name__}: {exc}")


def _snapshot_record(rt: _Runtime, incident_id: str) -> dict[str, Any] | None:
    """Rebuild a status record from the checkpoint DB (for pre-restart incidents)."""
    snap = rt.graph.get_state(run_config(incident_id, thread_id=incident_id))
    if not snap.values:
        return None
    status: Status = "paused_human_review" if snap.next == _HITL_NEXT else "completed"
    return {"incident_id": incident_id, "status": status,
            "recovered_from_checkpoint": True, **_summarize(snap.values)}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app(graph_factory: Any = None) -> FastAPI:
    """Build the FastAPI app.

    ``graph_factory`` (a zero-arg callable returning a compiled graph) is
    injectable so tests can serve a stub-LLM graph offline; the default builds
    the real pipeline with the SQLite checkpointer at startup — not at import —
    so importing this module never requires API keys.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        config.ensure_runtime_dirs()
        if graph_factory is not None:
            graph = graph_factory()
        else:
            from agents.supervisor import build_supervisor_graph, make_sqlite_checkpointer
            graph = build_supervisor_graph(checkpointer=make_sqlite_checkpointer())
        app.state.rt = _Runtime(graph)
        try:
            yield
        finally:
            app.state.rt.executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(
        title="Agentic Incident Response Server",
        version="1.0.0",
        description="REST deployment layer over the LangGraph incident-response pipeline.",
        lifespan=lifespan,
        dependencies=[Depends(require_api_key)],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        enabled, detail = tracing_status()
        return {
            "status": "ok",
            "llm_provider": config.LLM_PROVIDER,
            "run_mode": config.RUN_MODE,
            "langsmith_tracing": detail,
            "auth": "api-key" if os.getenv("SERVER_API_KEY") else "open",
        }

    @app.post("/incidents", status_code=202)
    def submit_incident(alert: AlertIn) -> dict[str, Any]:
        rt: _Runtime = app.state.rt
        state = create_initial_state(alert.model_dump(exclude_none=True))
        incident_id = state["incident_id"]

        existing = rt.get(incident_id)
        if existing and existing["status"] in ("running", "paused_human_review"):
            raise HTTPException(
                status_code=409,
                detail=f"incident {incident_id} is already {existing['status']}",
            )

        rt.update(incident_id, status="running", service_name=state["service_name"],
                  submitted_at=datetime.now(UTC).isoformat(), error=None)
        rt.executor.submit(_execute, rt, incident_id, state)
        return {"incident_id": incident_id, "status": "running",
                "status_url": f"/incidents/{incident_id}"}

    @app.get("/incidents")
    def list_incidents() -> list[dict[str, Any]]:
        rt: _Runtime = app.state.rt
        with rt.lock:
            return [dict(r) for r in rt.registry.values()]

    @app.get("/incidents/{incident_id}")
    def get_incident(incident_id: str) -> dict[str, Any]:
        rt: _Runtime = app.state.rt
        record = rt.get(incident_id) or _snapshot_record(rt, incident_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"unknown incident {incident_id}")
        return record

    @app.post("/incidents/{incident_id}/hitl", status_code=202)
    def hitl_decision(incident_id: str, body: HitlIn) -> dict[str, Any]:
        rt: _Runtime = app.state.rt
        record = rt.get(incident_id) or _snapshot_record(rt, incident_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"unknown incident {incident_id}")
        if record["status"] != "paused_human_review":
            raise HTTPException(
                status_code=409,
                detail=f"incident {incident_id} is {record['status']}, not paused for review",
            )
        rt.update(incident_id, status="running")
        rt.executor.submit(_execute, rt, incident_id, None, body.decision)
        return {"incident_id": incident_id, "decision": body.decision, "status": "running",
                "status_url": f"/incidents/{incident_id}"}

    @app.get("/incidents/{incident_id}/audit")
    def get_audit_trail(incident_id: str) -> dict[str, Any]:
        rt: _Runtime = app.state.rt
        # Finished runs have a persisted trail file (written by finalize, NFR-1).
        path = config.AUDIT_TRAIL_DIR / f"{incident_id}_audit.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return {"incident_id": incident_id, "source": "file",
                    "events": payload.get("events", [])}
        # In-flight / paused runs: read the trail from the checkpointed state.
        snap = rt.graph.get_state(run_config(incident_id, thread_id=incident_id))
        if not snap.values:
            raise HTTPException(status_code=404, detail=f"no audit trail for {incident_id}")
        events = [e.model_dump() if hasattr(e, "model_dump") else e
                  for e in snap.values.get("audit_trail", [])]
        return {"incident_id": incident_id, "source": "checkpoint", "events": events}

    @app.get("/dlq")
    def dlq() -> list[dict[str, Any]]:
        return [
            {"incident_id": e.incident_id, "reason": e.reason,
             "failure_type": e.failure_type, "total_steps": e.total_steps,
             "timestamp": e.timestamp}
            for e in review_dlq()
        ]

    return app


# uvicorn entry point: `uvicorn server.app:app --host 0.0.0.0 --port 8000`
app = create_app()
