"""MockMetricsAPI — simulates a metrics backend (Datadog/CloudWatch) (WI-12).

Returns current metric values for a service so the diagnosis subgraph's
``pull_metrics`` node has a second, independent data source (enabling graceful
degradation when logs fail but metrics succeed, and vice versa). Added under the
"additional tools" latitude of PRD §4.1; supports all failure modes.

Normal response shape: ``dict`` with ``service`` plus numeric metric fields.
"""

from __future__ import annotations

from typing import Any

from tools.base import MALFORMED_PAYLOAD, FailureMode, raise_if_exception_mode

#: Keys present on every well-formed metrics payload.
METRIC_KEYS: tuple[str, ...] = ("service", "error_rate", "latency_p95_ms")

# Per-service current readings. Numbers echo the seed incidents (checkout error
# spike, search-api memory pressure) so diagnosis has concrete signal to reason on.
_METRICS: dict[str, dict[str, Any]] = {
    "checkout": {
        "error_rate": 0.34, "latency_p95_ms": 1850, "cpu_pct": 71,
        "memory_pct": 63, "db_conn_wait": 57, "saturation": 0.92,
    },
    "search-api": {
        "error_rate": 0.06, "latency_p95_ms": 420, "cpu_pct": 88,
        "memory_pct": 96, "db_conn_wait": 2, "saturation": 0.97,
    },
}

_DEFAULT_METRICS: dict[str, Any] = {
    "error_rate": 0.02, "latency_p95_ms": 210, "cpu_pct": 40,
    "memory_pct": 55, "db_conn_wait": 0, "saturation": 0.5,
}


class MockMetricsAPI:
    """Mock metrics-query tool with injectable failure modes."""

    def __init__(
        self,
        failure_mode: FailureMode = FailureMode.NONE,
        metrics: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Create the tool. By default reads the shared fixture world; pass
        ``metrics`` to override with a custom per-service map (used in tests)."""
        self.failure_mode = failure_mode
        self.metrics = metrics  # None -> fall through to tools.fixtures

    def get_metrics(self, service_name: str) -> Any:
        """Return current metric readings for ``service_name``.

        Unknown services get baseline-healthy defaults (a valid, non-empty
        result). EMPTY mode returns ``{}`` (provider up, but no data for the
        window); MALFORMED returns an unparseable body.
        """
        raise_if_exception_mode(self.failure_mode, "MockMetricsAPI")
        if self.failure_mode == FailureMode.EMPTY:
            return {}
        if self.failure_mode == FailureMode.MALFORMED:
            return MALFORMED_PAYLOAD

        if self.metrics is not None:
            readings = self.metrics.get(service_name)
            if readings is not None:
                return {"service": service_name, **readings}
        from tools import fixtures
        return fixtures.metrics_for(service_name)
