"""Shared mock-data "world" for the tools (single source of truth).

The three data tools (logs, metrics, deployments) all read per-service fixtures
from here so a given service produces coherent, symptom-appropriate signals. This
is what makes a 20-incident evaluation meaningful: a memory-leak service returns
memory-leak logs/metrics (and a suspect deploy), while a novel-symptom service
returns signals that match no runbook (→ escalation).

Each service maps to a **symptom**. Symptoms whose logs contain a runbook's
keywords will match that runbook (→ high confidence → auto-resolve when a suspect
deploy is also present). "novel_*" symptoms deliberately avoid every runbook
keyword (→ no match → low confidence → escalate).

Mock data content is explicitly flexible per PRD §4.1.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Symptom → representative log lines (timestamp, level, message)
# ---------------------------------------------------------------------------
_SYMPTOM_LOGS: dict[str, list[tuple[str, str, str]]] = {
    "db_pool": [
        ("2026-07-26T01:58:12Z", "WARN", "db connection wait time rising"),
        ("2026-07-26T02:00:41Z", "ERROR", "connection pool exhausted (size=20, waiting=57)"),
        ("2026-07-26T02:00:44Z", "ERROR", "psycopg2.OperationalError: could not obtain connection"),
        ("2026-07-26T02:01:02Z", "ERROR", "database query aborted: pool timeout"),
    ],
    "memory": [
        ("2026-07-26T01:30:00Z", "WARN", "heap usage 88% and climbing"),
        ("2026-07-26T01:33:10Z", "ERROR", "OutOfMemoryError: java heap space"),
        ("2026-07-26T01:33:12Z", "ERROR", "pod OOMKilled, restarting container"),
        ("2026-07-26T01:35:00Z", "ERROR", "memory leak suspected in in-process cache"),
    ],
    "deploy_5xx": [
        ("2026-07-26T03:10:00Z", "INFO", "deploy rolled out to fleet"),
        ("2026-07-26T03:11:20Z", "ERROR", "500 Internal Server Error rate 41%"),
        ("2026-07-26T03:11:35Z", "ERROR", "unhandled exception in request handler after deploy"),
        ("2026-07-26T03:12:00Z", "ERROR", "5xx spike correlated with latest release (regression)"),
    ],
    "dep_timeout": [
        ("2026-07-26T04:05:00Z", "WARN", "upstream latency p95 climbing"),
        ("2026-07-26T04:06:10Z", "ERROR", "downstream dependency request timed out after 30s"),
        ("2026-07-26T04:06:22Z", "ERROR", "circuit breaker OPEN for downstream=payments-gateway"),
        ("2026-07-26T04:07:00Z", "ERROR", "upstream dependency unavailable, failing fast"),
    ],
    # ---- novel symptoms: match NO runbook keyword (drive escalation) ----
    "data_integrity": [
        ("2026-07-26T03:12:00Z", "ERROR", "ledger reconciliation discrepancy on 0.4% of records"),
        ("2026-07-26T03:12:30Z", "ERROR", "checksum validation failed for settlement batch"),
        ("2026-07-26T03:13:00Z", "ERROR", "financial hash mismatch, holding writes"),
    ],
    "security_breach": [
        ("2026-07-26T05:00:00Z", "ERROR", "anomalous access pattern from unexpected ASN"),
        ("2026-07-26T05:00:20Z", "ERROR", "privilege escalation attempt detected on admin route"),
        ("2026-07-26T05:01:00Z", "ERROR", "unusual bulk export initiated by service account"),
    ],
    "clock_skew": [
        ("2026-07-26T06:00:00Z", "WARN", "node clock drift 4200ms vs NTP source"),
        ("2026-07-26T06:00:30Z", "ERROR", "event ordering violation from time sync fault"),
        ("2026-07-26T06:01:00Z", "ERROR", "token nbf/exp window rejected: clock desync"),
    ],
    "cert_anomaly": [
        ("2026-07-26T07:00:00Z", "ERROR", "certificate chain validation error on mutual TLS"),
        ("2026-07-26T07:00:20Z", "ERROR", "handshake rejected: signing authority not recognized"),
        ("2026-07-26T07:01:00Z", "ERROR", "rotation produced an unexpected key fingerprint"),
    ],
    "planner_anomaly": [
        ("2026-07-26T08:00:00Z", "WARN", "query planner chose full scan over index"),
        ("2026-07-26T08:00:40Z", "ERROR", "execution plan cardinality estimate off by 1000x"),
        ("2026-07-26T08:01:00Z", "ERROR", "analytical job aborted: pathological join plan"),
    ],
    "healthy": [
        ("2026-07-26T00:00:00Z", "INFO", "healthcheck ok"),
        ("2026-07-26T00:01:00Z", "INFO", "no anomalies detected"),
    ],
}

# ---------------------------------------------------------------------------
# Symptom → current metric readings
# ---------------------------------------------------------------------------
_SYMPTOM_METRICS: dict[str, dict[str, Any]] = {
    "db_pool": {"error_rate": 0.34, "latency_p95_ms": 1850, "cpu_pct": 71,
                "memory_pct": 63, "db_conn_wait": 57, "saturation": 0.92},
    "memory": {"error_rate": 0.07, "latency_p95_ms": 430, "cpu_pct": 84,
               "memory_pct": 96, "db_conn_wait": 2, "saturation": 0.97},
    "deploy_5xx": {"error_rate": 0.41, "latency_p95_ms": 720, "cpu_pct": 60,
                   "memory_pct": 58, "db_conn_wait": 4, "saturation": 0.74},
    "dep_timeout": {"error_rate": 0.22, "latency_p95_ms": 4200, "cpu_pct": 48,
                    "memory_pct": 52, "db_conn_wait": 1, "saturation": 0.66},
    "data_integrity": {"error_rate": 0.004, "latency_p95_ms": 210, "cpu_pct": 40,
                       "memory_pct": 50, "db_conn_wait": 0, "saturation": 0.4},
    "security_breach": {"error_rate": 0.02, "latency_p95_ms": 260, "cpu_pct": 55,
                        "memory_pct": 57, "db_conn_wait": 1, "saturation": 0.6},
    "clock_skew": {"error_rate": 0.09, "latency_p95_ms": 300, "cpu_pct": 44,
                   "memory_pct": 54, "db_conn_wait": 0, "saturation": 0.5},
    "cert_anomaly": {"error_rate": 0.15, "latency_p95_ms": 350, "cpu_pct": 41,
                     "memory_pct": 53, "db_conn_wait": 0, "saturation": 0.55},
    "planner_anomaly": {"error_rate": 0.05, "latency_p95_ms": 9800, "cpu_pct": 92,
                        "memory_pct": 70, "db_conn_wait": 3, "saturation": 0.88},
    "healthy": {"error_rate": 0.01, "latency_p95_ms": 180, "cpu_pct": 35,
                "memory_pct": 48, "db_conn_wait": 0, "saturation": 0.4},
}

# ---------------------------------------------------------------------------
# Symptom → the summary line of the SUSPECT deploy that likely caused it
# ---------------------------------------------------------------------------
_SYMPTOM_SUSPECT_DEPLOY: dict[str, str] = {
    "db_pool": "Reduce DB connection pool size to cut idle connections",
    "memory": "Introduce in-memory result cache without eviction",
    "deploy_5xx": "Refactor request handler; new serialization path",
    "dep_timeout": "Lower client timeout on downstream dependency",
}

# ---------------------------------------------------------------------------
# Service registry: which symptom each service exhibits, and whether a suspect
# deployment exists (auto-resolvable services have one; novel ones do not).
# ---------------------------------------------------------------------------
SERVICES: dict[str, dict[str, Any]] = {
    # --- auto-resolvable (symptom matches a runbook + suspect deploy) ---
    "checkout": {"symptom": "db_pool", "suspect": True},
    "orders-api": {"symptom": "db_pool", "suspect": True},
    "user-profile": {"symptom": "db_pool", "suspect": True},
    "search-api": {"symptom": "memory", "suspect": True},
    "recommendations": {"symptom": "memory", "suspect": True},
    "catalog": {"symptom": "memory", "suspect": True},
    "payments-api": {"symptom": "deploy_5xx", "suspect": True},
    "cart-service": {"symptom": "deploy_5xx", "suspect": True},
    "inventory": {"symptom": "dep_timeout", "suspect": True},
    "shipping": {"symptom": "dep_timeout", "suspect": True},
    # --- escalation-required (novel symptom / no runbook / no suspect deploy) ---
    "billing-ledger": {"symptom": "data_integrity", "suspect": False},
    "fraud-detection": {"symptom": "security_breach", "suspect": False},
    "auth-service": {"symptom": "clock_skew", "suspect": False},
    "gateway": {"symptom": "cert_anomaly", "suspect": False},
    "analytics-warehouse": {"symptom": "planner_anomaly", "suspect": False},
}

_DEFAULT_SYMPTOM = "db_pool"


def _symptom_for(service_name: str) -> str:
    return str(SERVICES.get(service_name, {}).get("symptom", _DEFAULT_SYMPTOM))


def logs_for(service_name: str) -> list[dict[str, str]]:
    """Return symptom-appropriate log entries for a service."""
    symptom = _symptom_for(service_name)
    lines = _SYMPTOM_LOGS.get(symptom, _SYMPTOM_LOGS["healthy"])
    return [{"service": service_name, "timestamp": ts, "level": lvl, "message": msg}
            for ts, lvl, msg in lines]


def metrics_for(service_name: str) -> dict[str, Any]:
    """Return symptom-appropriate current metrics for a service."""
    symptom = _symptom_for(service_name)
    readings = _SYMPTOM_METRICS.get(symptom, _SYMPTOM_METRICS["healthy"])
    return {"service": service_name, **readings}


def deployments_for(service_name: str) -> list[dict[str, Any]]:
    """Return recent deployments; includes a suspect one for auto-resolvable services."""
    info = SERVICES.get(service_name, {})
    symptom = info.get("symptom", _DEFAULT_SYMPTOM)
    deploys: list[dict[str, Any]] = []
    if info.get("suspect"):
        deploys.append({
            "service": service_name, "sha": f"{abs(hash(service_name)) % 0xfffffff:07x}",
            "author": "dev-oncall", "timestamp": "2026-07-26T01:45:00Z",
            "summary": _SYMPTOM_SUSPECT_DEPLOY.get(symptom, "recent change"), "suspect": True,
        })
    deploys.append({
        "service": service_name, "sha": "0000abc", "author": "dev-ci",
        "timestamp": "2026-07-24T09:00:00Z", "summary": "Routine dependency bump", "suspect": False,
    })
    return deploys
