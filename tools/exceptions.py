"""Exception hierarchy raised by the mock (and later real) tools.

Each exception self-declares a semantic ``failure_type`` (one of ``config.FAILURE_*``)
and, where meaningful, an HTTP-style ``status_code``. The failure classifier reads
these attributes, so it never needs to import this module — keeping the utils layer
decoupled from the tools layer. Generic/third-party exceptions (e.g. the builtin
``TimeoutError``) are still classified correctly via status code and message scan.
"""

from __future__ import annotations

import config


class ToolError(Exception):
    """Base class for all tool failures. Defaults to the ``unknown`` failure type."""

    failure_type: str = config.FAILURE_UNKNOWN
    default_status_code: int | None = None

    def __init__(self, message: str = "", status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code: int | None = (
            status_code if status_code is not None else self.default_status_code
        )


class ToolTimeoutError(ToolError, TimeoutError):
    """The tool call timed out. Also subclasses builtin ``TimeoutError``."""

    failure_type = config.FAILURE_TIMEOUT


class RateLimitError(ToolError):
    """The tool was rate-limited (HTTP 429)."""

    failure_type = config.FAILURE_RATE_LIMIT
    default_status_code = 429


class AuthError(ToolError):
    """The tool call failed authentication/authorization (HTTP 401)."""

    failure_type = config.FAILURE_AUTH
    default_status_code = 401


class MalformedResponseError(ToolError):
    """The tool returned a response that could not be parsed as expected."""

    failure_type = config.FAILURE_MALFORMED
