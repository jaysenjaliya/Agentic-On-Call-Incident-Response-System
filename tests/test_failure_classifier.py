"""Unit tests for the failure classifier (WI-06) — the exact PRD release criteria."""

from __future__ import annotations

import pytest

import config
from tools.exceptions import AuthError, MalformedResponseError, RateLimitError, ToolTimeoutError
from utils.failure_classifier import classify_failure, classify_response


class TestClassifyFailure:
    """classify_failure maps: TimeoutError->timeout, 429->rate_limit, 401->auth, unknown->unknown."""

    def test_builtin_timeout_error(self) -> None:
        assert classify_failure(TimeoutError("timed out")) == config.FAILURE_TIMEOUT

    def test_tool_timeout_error(self) -> None:
        assert classify_failure(ToolTimeoutError("slow")) == config.FAILURE_TIMEOUT

    def test_rate_limit_via_exception(self) -> None:
        assert classify_failure(RateLimitError("too many")) == config.FAILURE_RATE_LIMIT

    def test_rate_limit_via_429_message(self) -> None:
        assert classify_failure(Exception("HTTP 429 returned")) == config.FAILURE_RATE_LIMIT

    def test_auth_via_exception(self) -> None:
        assert classify_failure(AuthError("nope")) == config.FAILURE_AUTH

    def test_auth_via_401_message(self) -> None:
        assert classify_failure(Exception("401 Unauthorized")) == config.FAILURE_AUTH

    def test_malformed_exception(self) -> None:
        assert classify_failure(MalformedResponseError("garbage")) == config.FAILURE_MALFORMED

    def test_unknown_default(self) -> None:
        assert classify_failure(Exception("something entirely novel")) == config.FAILURE_UNKNOWN

    @pytest.mark.parametrize(
        "status,expected",
        [(401, config.FAILURE_AUTH), (403, config.FAILURE_AUTH),
         (429, config.FAILURE_RATE_LIMIT), (408, config.FAILURE_TIMEOUT),
         (504, config.FAILURE_TIMEOUT)],
    )
    def test_status_code_mapping(self, status: int, expected: str) -> None:
        exc = Exception("boom")
        exc.status_code = status  # type: ignore[attr-defined]
        assert classify_failure(exc) == expected

    def test_result_is_always_a_known_type(self) -> None:
        assert classify_failure(Exception("x")) in config.FAILURE_TYPES


class TestClassifyResponse:
    """classify_response distinguishes ok / empty (not error) / malformed (is error)."""

    def test_ok_list(self) -> None:
        assert classify_response([{"a": 1}]) == config.RESPONSE_OK

    def test_ok_dict(self) -> None:
        assert classify_response({"status": "sent"}) == config.RESPONSE_OK

    def test_empty_list_is_not_error(self) -> None:
        assert classify_response([]) == config.RESPONSE_EMPTY

    def test_empty_dict_is_not_error(self) -> None:
        assert classify_response({}) == config.RESPONSE_EMPTY

    def test_none_is_empty(self) -> None:
        assert classify_response(None) == config.RESPONSE_EMPTY

    def test_blank_string_is_empty(self) -> None:
        assert classify_response("   ") == config.RESPONSE_EMPTY

    def test_raw_string_is_malformed(self) -> None:
        assert classify_response('{"truncated": ') == config.RESPONSE_MALFORMED

    def test_scalar_is_malformed(self) -> None:
        assert classify_response(42) == config.RESPONSE_MALFORMED

    def test_missing_required_keys_dict_is_malformed(self) -> None:
        assert classify_response({"wrong": 1}, required_keys=["msg"]) == config.RESPONSE_MALFORMED

    def test_missing_required_keys_list_item_is_malformed(self) -> None:
        assert classify_response([{"msg": "x"}, {"no": 1}], required_keys=["msg"]) == config.RESPONSE_MALFORMED

    def test_present_required_keys_is_ok(self) -> None:
        assert classify_response([{"msg": "x"}], required_keys=["msg"]) == config.RESPONSE_OK
