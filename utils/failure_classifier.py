"""Adaptive failure classification — novelty feature #1 (PRD §1.4, FR-5).

Standard agentic demos treat every tool error the same and just count retries.
This module classifies errors **semantically** so downstream nodes can route each
class to a different recovery strategy:

    timeout     -> transient; retry with backoff
    rate_limit  -> back off longer; retry
    auth        -> not retryable; escalate (a human must fix credentials)
    malformed   -> the call "succeeded" but the payload is garbage; retry/degrade
    unknown     -> conservative default; limited retry then escalate

Two entry points:
    classify_failure(exc)      -- map a raised exception to a failure type.
    classify_response(resp)    -- distinguish ok / empty (not an error) / malformed.

The classifier depends only on ``config`` and duck-types exceptions (reading
``failure_type`` / ``status_code`` attributes and scanning the message), so it
works for both our tool exceptions and arbitrary third-party ones.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import config

# ---------------------------------------------------------------------------
# Exception -> failure type
# ---------------------------------------------------------------------------
# Keyword hints scanned in the exception message as a last resort. Order matters:
# more specific phrases first.
_MESSAGE_HINTS: tuple[tuple[str, str], ...] = (
    ("timed out", config.FAILURE_TIMEOUT),
    ("timeout", config.FAILURE_TIMEOUT),
    ("too many requests", config.FAILURE_RATE_LIMIT),
    ("rate limit", config.FAILURE_RATE_LIMIT),
    ("ratelimit", config.FAILURE_RATE_LIMIT),
    ("429", config.FAILURE_RATE_LIMIT),
    ("unauthorized", config.FAILURE_AUTH),
    ("forbidden", config.FAILURE_AUTH),
    ("authentication", config.FAILURE_AUTH),
    ("permission denied", config.FAILURE_AUTH),
    ("401", config.FAILURE_AUTH),
    ("403", config.FAILURE_AUTH),
    ("malformed", config.FAILURE_MALFORMED),
    ("could not parse", config.FAILURE_MALFORMED),
    ("json", config.FAILURE_MALFORMED),
)

# HTTP status code -> failure type.
_STATUS_MAP: dict[int, str] = {
    401: config.FAILURE_AUTH,
    403: config.FAILURE_AUTH,
    408: config.FAILURE_TIMEOUT,
    429: config.FAILURE_RATE_LIMIT,
    504: config.FAILURE_TIMEOUT,
}


def classify_failure(exc: BaseException) -> str:
    """Map a raised exception to a semantic failure type (one of ``config.FAILURE_*``).

    Reads: the exception's ``failure_type`` attribute (if it self-declares one),
    its ``status_code``, its type, and finally its message text.
    Returns: a ``config.FAILURE_*`` string. Falls back to ``unknown`` — never raises.
    Decision: selects the recovery strategy bucket for the calling node.

    Resolution order (most authoritative first):
        1. explicit ``failure_type`` attribute on the exception
        2. ``status_code`` attribute mapped via ``_STATUS_MAP``
        3. builtin ``TimeoutError`` instance
        4. keyword scan of the message
        5. ``unknown``
    """
    # 1. Self-declared failure type (our ToolError subclasses).
    declared = getattr(exc, "failure_type", None)
    if isinstance(declared, str) and declared in config.FAILURE_TYPES:
        return declared

    # 2. HTTP-style status code.
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status in _STATUS_MAP:
        return _STATUS_MAP[status]

    # 3. Builtin timeout (covers TimeoutError from stdlib / sockets).
    if isinstance(exc, TimeoutError):
        return config.FAILURE_TIMEOUT

    # 4. Message keyword scan.
    message = str(exc).lower()
    for hint, failure_type in _MESSAGE_HINTS:
        if hint in message:
            return failure_type

    # 5. Give up gracefully.
    return config.FAILURE_UNKNOWN


# ---------------------------------------------------------------------------
# Response -> ok / empty / malformed
# ---------------------------------------------------------------------------
def classify_response(
    response: Any,
    required_keys: Sequence[str] | None = None,
) -> str:
    """Classify a tool's (non-exception) response as ok / empty / malformed.

    Reads: the response value and, optionally, ``required_keys`` that a valid
    structured payload (or each item of a list payload) must contain.
    Returns: ``config.RESPONSE_OK``, ``RESPONSE_EMPTY``, or ``RESPONSE_MALFORMED``.
    Decision: distinguishes a valid "no data" result (empty — NOT an error) from a
    genuinely broken payload (malformed — IS an error). This distinction is the
    point: an empty log query is normal; a truncated JSON blob is a failure.

    Conventions:
        * ``None`` and empty containers -> empty.
        * A raw ``str`` where structured data is expected -> malformed
          (blank string -> empty). Tools return parsed objects, not text.
        * ``required_keys`` missing from a dict, or from any item of a list of
          dicts -> malformed.
        * Unexpected scalar types (int, float, bool) -> malformed.
    """
    # Empty / no data.
    if response is None:
        return config.RESPONSE_EMPTY

    if isinstance(response, str):
        return config.RESPONSE_EMPTY if response.strip() == "" else config.RESPONSE_MALFORMED

    if isinstance(response, (list, tuple, set, dict)):
        if len(response) == 0:
            return config.RESPONSE_EMPTY

        if required_keys:
            if isinstance(response, dict):
                if not all(k in response for k in required_keys):
                    return config.RESPONSE_MALFORMED
            elif isinstance(response, (list, tuple)):
                for item in response:
                    if not isinstance(item, dict) or not all(k in item for k in required_keys):
                        return config.RESPONSE_MALFORMED
        return config.RESPONSE_OK

    # Any other type (scalars, objects) is not a shape we expect from a tool.
    return config.RESPONSE_MALFORMED
