"""Tools package — mock observability/notification tools with injectable failures.

Each mock tool exposes failure modes (timeout, rate_limit, auth, empty, malformed)
so the adaptive failure classifier can be exercised end-to-end. Real MCP tools
(e.g. Gmail) are added in Phase 3.
"""

from tools.base import FailureMode
from tools.exceptions import (
    AuthError,
    MalformedResponseError,
    RateLimitError,
    ToolError,
    ToolTimeoutError,
)
from tools.mock_github_api import MockGitHubAPI
from tools.mock_log_api import MockLogAPI
from tools.mock_notification import MockNotificationService
from tools.mock_runbook_search import MockRunbookSearch

__all__ = [
    "FailureMode",
    "MockLogAPI",
    "MockRunbookSearch",
    "MockGitHubAPI",
    "MockNotificationService",
    "ToolError",
    "ToolTimeoutError",
    "RateLimitError",
    "AuthError",
    "MalformedResponseError",
]
