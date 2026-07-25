"""Unit tests for the four mock tools (WI-02..05), each in isolation.

Verifies: happy path returns well-formed data; raising modes raise the correct
exception; empty/malformed modes return correctly-classifiable payloads.
"""

from __future__ import annotations

import pytest

import config
from tools import MockGitHubAPI, MockLogAPI, MockNotificationService, MockRunbookSearch
from tools.base import RAISING_MODES, FailureMode
from tools.exceptions import AuthError, RateLimitError, ToolTimeoutError
from tools.mock_github_api import DEPLOYMENT_KEYS
from tools.mock_log_api import LOG_ENTRY_KEYS
from tools.mock_notification import RECEIPT_KEYS
from tools.mock_runbook_search import RUNBOOK_KEYS
from utils.failure_classifier import classify_failure, classify_response

# (tool factory, invoke callable, required-keys) for parametrized coverage.
TOOL_CASES = [
    pytest.param(lambda m: MockLogAPI(m), lambda t: t.fetch_logs("checkout"), LOG_ENTRY_KEYS, id="log"),
    pytest.param(lambda m: MockRunbookSearch(m),
                 lambda t: t.search("connection pool exhausted psycopg2 database"), RUNBOOK_KEYS, id="runbook"),
    pytest.param(lambda m: MockGitHubAPI(m),
                 lambda t: t.get_recent_deployments("checkout"), DEPLOYMENT_KEYS, id="github"),
    pytest.param(lambda m: MockNotificationService(m),
                 lambda t: t.send("a@b.com", "s", "b"), RECEIPT_KEYS, id="notify"),
]

_EXPECTED_FAILURE = {
    FailureMode.TIMEOUT: config.FAILURE_TIMEOUT,
    FailureMode.RATE_LIMIT: config.FAILURE_RATE_LIMIT,
    FailureMode.AUTH: config.FAILURE_AUTH,
}


@pytest.mark.parametrize("factory,invoke,keys", TOOL_CASES)
class TestEveryTool:
    def test_happy_path_ok(self, factory, invoke, keys) -> None:
        result = invoke(factory(FailureMode.NONE))
        assert classify_response(result, required_keys=keys) == config.RESPONSE_OK

    @pytest.mark.parametrize("mode", sorted(RAISING_MODES))
    def test_raising_modes(self, factory, invoke, keys, mode) -> None:
        with pytest.raises(Exception) as excinfo:
            invoke(factory(mode))
        assert classify_failure(excinfo.value) == _EXPECTED_FAILURE[mode]

    def test_empty_mode(self, factory, invoke, keys) -> None:
        assert classify_response(invoke(factory(FailureMode.EMPTY))) == config.RESPONSE_EMPTY

    def test_malformed_mode(self, factory, invoke, keys) -> None:
        assert classify_response(invoke(factory(FailureMode.MALFORMED))) == config.RESPONSE_MALFORMED


class TestToolSpecifics:
    """A few behaviours beyond the generic contract."""

    def test_exception_types_are_specific(self) -> None:
        with pytest.raises(ToolTimeoutError):
            MockLogAPI(FailureMode.TIMEOUT).fetch_logs("x")
        with pytest.raises(RateLimitError):
            MockLogAPI(FailureMode.RATE_LIMIT).fetch_logs("x")
        with pytest.raises(AuthError):
            MockLogAPI(FailureMode.AUTH).fetch_logs("x")

    def test_runbook_keyword_match_returns_rb101(self) -> None:
        matches = MockRunbookSearch().search("connection pool exhausted psycopg2 database")
        assert matches and matches[0]["runbook_id"] == "RB-101"

    def test_runbook_unknown_issue_returns_empty(self) -> None:
        # No keyword overlap -> empty result -> drives escalation.
        assert MockRunbookSearch().search("quantum flux capacitor anomaly") == []

    def test_github_suspect_deploy_present_for_checkout(self) -> None:
        deploys = MockGitHubAPI().get_recent_deployments("checkout")
        assert any(d["suspect"] for d in deploys)

    def test_notification_records_sent_messages(self) -> None:
        svc = MockNotificationService()
        svc.send("oncall@example.com", "INC-1", "down")
        assert len(svc.sent) == 1 and svc.sent[0]["to"] == "oncall@example.com"
