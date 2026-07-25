"""Tests for the resilient tool-calling loop (utils/tool_runner)."""

from __future__ import annotations

import config
from tools.exceptions import AuthError, RateLimitError, ToolTimeoutError
from utils.tool_runner import run_tool

NOOP = lambda *_: None  # noqa: E731


class TestRunTool:
    def test_success_first_try(self):
        out = run_tool("T", lambda: [{"a": 1}], sleep=NOOP)
        assert out.ok and out.attempts == 1 and out.response_class == config.RESPONSE_OK

    def test_empty_is_ok_not_failure(self):
        out = run_tool("T", lambda: [], sleep=NOOP)
        assert out.ok and out.response_class == config.RESPONSE_EMPTY

    def test_persistent_timeout_retries_then_fails(self):
        calls = {"n": 0}

        def call():
            calls["n"] += 1
            raise ToolTimeoutError("slow")

        out = run_tool("T", call, sleep=NOOP)
        assert out.ok is False
        assert out.failure_type == config.FAILURE_TIMEOUT
        # initial + MAX_RETRIES retries
        assert out.attempts == config.MAX_RETRIES_PER_TOOL + 1
        assert calls["n"] == config.MAX_RETRIES_PER_TOOL + 1

    def test_auth_is_not_retried(self):
        calls = {"n": 0}

        def call():
            calls["n"] += 1
            raise AuthError("401")

        out = run_tool("T", call, sleep=NOOP)
        assert out.ok is False and out.failure_type == config.FAILURE_AUTH
        assert calls["n"] == 1  # tried once, gave up immediately

    def test_recovers_after_transient_failure(self):
        calls = {"n": 0}

        def call():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RateLimitError("429")
            return [{"ok": True}]

        out = run_tool("T", call, sleep=NOOP)
        assert out.ok is True and out.attempts == 2

    def test_malformed_response_is_retried(self):
        out = run_tool("T", lambda: "<<<garbled", sleep=NOOP)
        assert out.ok is False
        assert out.failure_type == config.FAILURE_MALFORMED
        assert out.attempts == config.MAX_RETRIES_PER_TOOL + 1

    def test_backoff_uses_injected_sleep(self):
        waits: list[float] = []

        def call():
            raise ToolTimeoutError("slow")

        run_tool("T", call, sleep=waits.append)
        # One sleep between each of the retries.
        assert waits == list(config.RETRY_BACKOFF_SECONDS[: config.MAX_RETRIES_PER_TOOL])
