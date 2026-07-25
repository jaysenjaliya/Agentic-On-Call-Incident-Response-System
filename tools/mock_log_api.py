"""MockLogAPI — simulates a log backend (Datadog/CloudWatch) (WI-02).

Returns recent log lines for a service. Supports all failure modes so the
diagnosis subgraph's ``pull_logs`` node can be tested against real failure paths
without a live backend (PRD §4.2 permits mock observability tools).

Normal response shape: ``list[dict]`` where each entry has
``timestamp``, ``level``, ``service``, ``message``.
"""

from __future__ import annotations

from typing import Any

from tools.base import MALFORMED_PAYLOAD, FailureMode, raise_if_exception_mode

#: The keys every well-formed log entry contains (used by classify_response checks).
LOG_ENTRY_KEYS: tuple[str, ...] = ("timestamp", "level", "service", "message")

# A small, service-agnostic bank of representative log lines. Enough signal for the
# diagnosis LLM to reason about (error spikes, stack traces) without a live source.
# Built from (timestamp, level, message) triples to keep each entry readable.
_DEFAULT_LOG_LINES: list[tuple[str, str, str]] = [
    ("2026-07-25T01:58:12Z", "INFO", "healthcheck ok"),
    ("2026-07-25T02:00:03Z", "WARN", "latency p95 rising: 480ms"),
    ("2026-07-25T02:00:41Z", "ERROR", "connection pool exhausted (size=20, waiting=57)"),
    ("2026-07-25T02:00:44Z", "ERROR", "psycopg2.OperationalError: could not obtain connection"),
    ("2026-07-25T02:01:02Z", "ERROR", "500 Internal Server Error rate 34%"),
    ("2026-07-25T02:01:15Z", "ERROR", "circuit breaker OPEN for downstream=payments-db"),
]
_DEFAULT_LOGS: list[dict[str, str]] = [
    {"timestamp": ts, "level": level, "message": msg} for ts, level, msg in _DEFAULT_LOG_LINES
]


class MockLogAPI:
    """Mock log-query tool with injectable failure modes."""

    def __init__(self, failure_mode: FailureMode = FailureMode.NONE) -> None:
        """Create the tool. ``failure_mode`` fixes the behaviour of every call."""
        self.failure_mode = failure_mode

    def fetch_logs(self, service_name: str, limit: int = 50) -> Any:
        """Return recent log entries for ``service_name`` (newest last).

        Returns ``Any`` because this models an external boundary: the happy path
        yields ``list[dict]`` (see ``LOG_ENTRY_KEYS``), EMPTY yields ``[]``, and
        MALFORMED yields an unparseable string. Raising modes raise before return.
        """
        raise_if_exception_mode(self.failure_mode, "MockLogAPI")
        if self.failure_mode == FailureMode.EMPTY:
            return []
        if self.failure_mode == FailureMode.MALFORMED:
            return MALFORMED_PAYLOAD
        return [{"service": service_name, **entry} for entry in _DEFAULT_LOGS[:limit]]
