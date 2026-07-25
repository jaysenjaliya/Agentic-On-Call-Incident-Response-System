"""MockRunbookSearch — simulates a runbook knowledge base (Confluence) (WI-03).

Keyword-matches an incident description against a small in-memory runbook KB and
returns candidate runbooks ranked by overlap. Feeds the root-cause subgraph's
``search_runbooks`` node (FR-3). Supports all failure modes.

Normal response shape: ``list[dict]`` where each match has
``runbook_id``, ``title``, ``keywords``, ``root_cause``, ``remediation_steps``,
``score``.
"""

from __future__ import annotations

from typing import Any

from tools.base import MALFORMED_PAYLOAD, FailureMode, raise_if_exception_mode

#: Keys present on every well-formed runbook match.
RUNBOOK_KEYS: tuple[str, ...] = ("runbook_id", "title", "root_cause", "remediation_steps")

# In-memory runbook KB. Each entry pairs symptom keywords with a known root cause
# and concrete remediation steps. Seed incidents are written to match these so the
# end-to-end pipeline can auto-resolve.
_RUNBOOKS: list[dict[str, Any]] = [
    {
        "runbook_id": "RB-101",
        "title": "Database connection pool exhaustion",
        "keywords": ["connection pool", "exhausted", "psycopg2", "database", "db",
                     "operationalerror"],
        "root_cause": "Connection pool too small for current load; connections not released.",
        "remediation_steps": [
            "Increase pool size from 20 to 50",
            "Recycle stale connections",
            "Verify no connection leaks in recent deploy",
        ],
    },
    {
        "runbook_id": "RB-102",
        "title": "Memory leak causing OOM restarts",
        "keywords": ["memory", "oom", "out of memory", "heap", "leak", "restart"],
        "root_cause": "Unbounded in-memory cache growth leading to OOM kills.",
        "remediation_steps": [
            "Enable cache TTL/eviction",
            "Roll back to previous release",
            "Increase memory limit temporarily",
        ],
    },
    {
        "runbook_id": "RB-103",
        "title": "Elevated 5xx after deployment",
        "keywords": ["500", "5xx", "internal server error", "deploy", "regression", "error rate"],
        "root_cause": "Regression introduced by a recent deployment.",
        "remediation_steps": [
            "Roll back the offending deployment",
            "Re-run smoke tests",
            "Notify the deploying team",
        ],
    },
    {
        "runbook_id": "RB-104",
        "title": "Upstream dependency timeout / circuit breaker open",
        "keywords": ["timeout", "circuit breaker", "upstream", "downstream", "latency",
                     "dependency"],
        "root_cause": "A downstream dependency is slow, tripping circuit breakers.",
        "remediation_steps": [
            "Increase client timeout and retries",
            "Fail over to secondary region",
            "Page the downstream service owner",
        ],
    },
]


class MockRunbookSearch:
    """Mock runbook search with keyword matching and injectable failure modes."""

    def __init__(
        self,
        failure_mode: FailureMode = FailureMode.NONE,
        runbooks: list[dict[str, Any]] | None = None,
    ) -> None:
        """Create the tool. Optionally override the runbook KB (defaults to ``_RUNBOOKS``)."""
        self.failure_mode = failure_mode
        self.runbooks = runbooks if runbooks is not None else _RUNBOOKS

    def search(self, query: str, top_k: int = 3) -> Any:
        """Return runbooks whose keywords appear in ``query``, ranked by score.

        Score = count of distinct runbook keywords found in the lowercased query.
        Runbooks with zero matches are excluded — so a query about an unknown issue
        legitimately returns ``[]`` (empty, not an error), which drives escalation.
        """
        raise_if_exception_mode(self.failure_mode, "MockRunbookSearch")
        if self.failure_mode == FailureMode.EMPTY:
            return []
        if self.failure_mode == FailureMode.MALFORMED:
            return MALFORMED_PAYLOAD

        q = query.lower()
        scored: list[dict[str, Any]] = []
        for rb in self.runbooks:
            score = sum(1 for kw in rb["keywords"] if kw in q)
            if score > 0:
                match = {k: rb[k] for k in RUNBOOK_KEYS}
                match["keywords"] = rb["keywords"]
                match["score"] = score
                scored.append(match)
        scored.sort(key=lambda m: m["score"], reverse=True)
        return scored[:top_k]
