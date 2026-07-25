"""Reusable tool-calling recovery loop — the heart of the Phase 2 node pattern.

Every tool-calling node must: try the call → on exception classify the failure →
route to a recovery strategy → retry with backoff (max 3) → and end with a single
audit event (PRD §3.2, FR-5). Rather than copy that logic into six nodes, they all
call :func:`run_tool`, which returns a structured :class:`ToolOutcome` the node
turns into state updates + one audit event.

Recovery strategy by classified failure type:
    timeout / rate_limit / unknown / malformed -> retryable (backoff, then retry)
    auth                                        -> NOT retryable (stop immediately;
                                                   a human must fix credentials)

A malformed *response* (not an exception) is treated as a retryable failure — the
call "succeeded" but returned garbage. An *empty* response is a valid no-data
result (``ok``), never an error (this is what enables graceful degradation).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import config
from utils.failure_classifier import classify_failure, classify_response

#: Failure types worth retrying. ``auth`` is deliberately excluded.
RETRYABLE_FAILURES: frozenset[str] = frozenset({
    config.FAILURE_TIMEOUT,
    config.FAILURE_RATE_LIMIT,
    config.FAILURE_UNKNOWN,
    config.FAILURE_MALFORMED,
})


@dataclass
class ToolOutcome:
    """Result of a resilient tool invocation.

    ``ok`` is True when usable data was obtained (including a valid *empty*
    result). When False, ``failure_type`` / ``error`` describe why, after all
    retries were exhausted or a non-retryable failure occurred.
    """

    ok: bool
    data: Any
    response_class: str | None  # config.RESPONSE_* when a response was received
    failure_type: str | None    # config.FAILURE_* on failure
    error: str | None           # human-readable last error
    attempts: int               # total attempts made (1 = no retries)


def run_tool(
    tool_name: str,
    call: Callable[[], Any],
    *,
    required_keys: Sequence[str] | None = None,
    max_retries: int = config.MAX_RETRIES_PER_TOOL,
    backoff: Sequence[int] = config.RETRY_BACKOFF_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> ToolOutcome:
    """Invoke ``call`` with adaptive failure handling and bounded retries.

    Reads nothing from state (pure). Returns a :class:`ToolOutcome`. ``sleep`` is
    injectable so tests run without real delays. One call to this function
    corresponds to one node execution → one audit event (the node writes it).
    """
    last_failure: str | None = None
    last_error: str | None = None
    attempts = 0

    for attempt in range(max_retries + 1):  # initial attempt + up to max_retries
        attempts = attempt + 1
        try:
            response = call()
        except Exception as exc:  # noqa: BLE001 - classification is the whole point
            last_failure = classify_failure(exc)
            last_error = f"{type(exc).__name__}: {exc}"
            if last_failure not in RETRYABLE_FAILURES:
                break  # e.g. auth — not retryable
        else:
            response_class = classify_response(response, required_keys=required_keys)
            if response_class != config.RESPONSE_MALFORMED:
                # ok or empty -> usable data (graceful degradation on empty).
                return ToolOutcome(
                    ok=True, data=response, response_class=response_class,
                    failure_type=None, error=None, attempts=attempts,
                )
            last_failure = config.FAILURE_MALFORMED
            last_error = f"{tool_name} returned a malformed response"

        # Retryable failure: back off before the next attempt (if any remain).
        if attempt < max_retries:
            sleep(backoff[min(attempt, len(backoff) - 1)])

    return ToolOutcome(
        ok=False, data=None, response_class=None,
        failure_type=last_failure, error=last_error, attempts=attempts,
    )
