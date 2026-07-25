"""Shared failure-injection machinery for the mock tools.

Every mock tool accepts a ``FailureMode`` so tests and the evaluation harness can
deterministically exercise the failure-handling paths (FR-5). Three modes raise
exceptions (timeout / rate_limit / auth); two modes return non-exception payloads
that the response classifier must catch (empty / malformed). ``NONE`` is the happy
path.

This split is deliberate: ``classify_failure`` handles the raising modes, while
``classify_response`` handles empty-vs-malformed — both novelty paths are covered.
"""

from __future__ import annotations

from enum import StrEnum

from tools.exceptions import AuthError, MalformedResponseError, RateLimitError, ToolTimeoutError


class FailureMode(StrEnum):
    """Injectable behaviours for a mock tool.

    Raising modes -> caught by ``classify_failure``:
        TIMEOUT, RATE_LIMIT, AUTH
    Returning modes -> caught by ``classify_response``:
        EMPTY (valid "no data", not an error), MALFORMED (broken payload, an error)
    """

    NONE = "none"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    EMPTY = "empty"
    MALFORMED = "malformed"


#: The modes that raise (as opposed to returning a classifiable payload).
RAISING_MODES: frozenset[FailureMode] = frozenset(
    {FailureMode.TIMEOUT, FailureMode.RATE_LIMIT, FailureMode.AUTH}
)

#: A truncated-JSON string standing in for an unparseable API body.
MALFORMED_PAYLOAD: str = '{"results": [ {"id": "wat", "sever'


def raise_if_exception_mode(mode: FailureMode, tool_name: str) -> None:
    """Raise the exception corresponding to a raising ``FailureMode``, else no-op.

    Called at the top of every mock tool method. For non-raising modes (NONE,
    EMPTY, MALFORMED) it returns silently and the caller shapes the payload.
    """
    if mode == FailureMode.TIMEOUT:
        raise ToolTimeoutError(f"{tool_name}: request timed out after 30s")
    if mode == FailureMode.RATE_LIMIT:
        raise RateLimitError(f"{tool_name}: 429 too many requests")
    if mode == FailureMode.AUTH:
        raise AuthError(f"{tool_name}: 401 unauthorized — invalid API token")


def malformed_error(tool_name: str) -> MalformedResponseError:
    """Build (do not raise) a ``MalformedResponseError`` for a tool.

    Provided for nodes that prefer to convert a malformed *response* into a raised
    failure; the tools themselves return ``MALFORMED_PAYLOAD`` so the response
    classifier path is also exercisable.
    """
    return MalformedResponseError(f"{tool_name}: could not parse response body")
