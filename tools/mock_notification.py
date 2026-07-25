"""MockNotificationService — simulates paging/email (WI-05).

Stands in for the real Gmail MCP tool in mock mode (RUN_MODE=mock). Used by the
remediation subgraph's ``escalate`` node to notify a human. Records sent messages
in-memory so tests can assert on them. Supports all failure modes.

Normal response shape: ``dict`` with
``status``, ``channel``, ``to``, ``subject``, ``message_id``, ``timestamp``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from tools.base import MALFORMED_PAYLOAD, FailureMode, raise_if_exception_mode

#: Keys present on every well-formed send receipt.
RECEIPT_KEYS: tuple[str, ...] = ("status", "to", "subject", "message_id")


class MockNotificationService:
    """Mock notification/paging tool with injectable failure modes."""

    def __init__(self, failure_mode: FailureMode = FailureMode.NONE) -> None:
        """Create the tool. Sent messages accumulate in ``self.sent`` for assertions."""
        self.failure_mode = failure_mode
        self.sent: list[dict[str, Any]] = []

    def send(self, to: str, subject: str, body: str, channel: str = "email") -> Any:
        """Send a notification and return a delivery receipt.

        Reads: recipient, subject, body. Writes: appends to ``self.sent`` on the
        happy path. EMPTY mode simulates a provider that accepted the request but
        returned no receipt body (``{}``); MALFORMED returns an unparseable body.
        """
        raise_if_exception_mode(self.failure_mode, "MockNotificationService")
        if self.failure_mode == FailureMode.EMPTY:
            return {}
        if self.failure_mode == FailureMode.MALFORMED:
            return MALFORMED_PAYLOAD

        receipt: dict[str, Any] = {
            "status": "sent",
            "channel": channel,
            "to": to,
            "subject": subject,
            "message_id": f"msg-{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.sent.append(receipt)
        return receipt
