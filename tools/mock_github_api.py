"""MockGitHubAPI — simulates the GitHub deployments API (WI-04).

Returns recent deployments for a service so the root-cause subgraph's
``check_deployments`` node can correlate incidents with regressions (FR-3).
Supports all failure modes.

Normal response shape: ``list[dict]`` where each deployment has
``sha``, ``service``, ``author``, ``timestamp``, ``summary``, ``suspect``.
"""

from __future__ import annotations

from typing import Any

from tools.base import MALFORMED_PAYLOAD, FailureMode, raise_if_exception_mode

#: Keys present on every well-formed deployment record.
DEPLOYMENT_KEYS: tuple[str, ...] = ("sha", "service", "author", "timestamp", "summary")

# Per-service deployment history. ``suspect: True`` marks a deploy shortly before an
# incident window — the root-cause node uses recency/suspect to hypothesize a
# regression. Services absent here return the generic history.
_DEPLOYMENTS: dict[str, list[dict[str, Any]]] = {
    "checkout": [
        {"sha": "a1b2c3d", "author": "dev-priya", "timestamp": "2026-07-25T01:45:00Z",
         "summary": "Reduce DB pool size to cut idle connections", "suspect": True},
        {"sha": "9f8e7d6", "author": "dev-sam", "timestamp": "2026-07-24T18:10:00Z",
         "summary": "Add retry to payment gateway client", "suspect": False},
    ],
    "search-api": [
        {"sha": "c0ffee1", "author": "dev-lee", "timestamp": "2026-07-25T01:30:00Z",
         "summary": "Introduce in-memory result cache", "suspect": True},
        {"sha": "deadbea", "author": "dev-mo", "timestamp": "2026-07-23T09:00:00Z",
         "summary": "Upgrade elasticsearch client", "suspect": False},
    ],
}

_GENERIC_HISTORY: list[dict[str, Any]] = [
    {"sha": "0000abc", "author": "dev-ci", "timestamp": "2026-07-22T12:00:00Z",
     "summary": "Routine dependency bump", "suspect": False},
]


class MockGitHubAPI:
    """Mock deployments API with injectable failure modes."""

    def __init__(
        self,
        failure_mode: FailureMode = FailureMode.NONE,
        deployments: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        """Create the tool. By default reads the shared fixture world; pass
        ``deployments`` to override with a custom history map (used in tests)."""
        self.failure_mode = failure_mode
        self.deployments = deployments  # None -> fall through to tools.fixtures

    def get_recent_deployments(self, service_name: str, limit: int = 10) -> Any:
        """Return recent deployments for ``service_name`` (newest first).

        Auto-resolvable services include a ``suspect`` deploy; novel ones don't.
        EMPTY mode returns ``[]`` (service exists but no recent deploys).
        """
        raise_if_exception_mode(self.failure_mode, "MockGitHubAPI")
        if self.failure_mode == FailureMode.EMPTY:
            return []
        if self.failure_mode == FailureMode.MALFORMED:
            return MALFORMED_PAYLOAD

        if self.deployments is not None:
            history = self.deployments.get(service_name, _GENERIC_HISTORY)
            return [{"service": service_name, **dep} for dep in history[:limit]]
        from tools import fixtures
        return fixtures.deployments_for(service_name)[:limit]
