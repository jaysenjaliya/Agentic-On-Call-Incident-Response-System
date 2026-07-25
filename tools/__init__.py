"""Tools package — mock observability/notification tools with injectable failures.

Each mock tool exposes at least 3 configurable failure modes (timeout, rate_limit,
empty, malformed) so the adaptive failure classifier can be exercised end-to-end.
Real MCP tools (e.g. Gmail) are added in Phase 3.

Contents (implemented in Phase 1 — Foundation):
    mock_log_api.py           -- MockLogAPI (WI-02)
    mock_runbook_search.py    -- MockRunbookSearch, keyword matching (WI-03)
    mock_github_api.py        -- MockGitHubAPI, deployment history (WI-04)
    mock_notification.py      -- MockNotificationService (WI-05)

Status: PLACEHOLDER — see docs/PHASES.md (Phase 1, WI-02..WI-05).
"""
