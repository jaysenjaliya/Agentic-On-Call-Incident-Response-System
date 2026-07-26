"""Notifier factory — selects the escalation channel by config.

Returns an object exposing ``.send(to, subject, body)``. In mock mode (default)
that's the in-memory ``MockNotificationService``; when Gmail MCP is enabled
(RUN_MODE=prod + GMAIL_MCP_ENABLED=true) it's the real Gmail MCP notifier (WI-32).

Keeping this behind one factory means the escalate node never changes when we
flip from mock to real — exactly the PRD §7.2 risk-mitigation design.
"""

from __future__ import annotations

from typing import Any

import config


def get_notifier() -> Any:
    """Return the configured notifier (mock by default; Gmail MCP when enabled)."""
    if config.RUN_MODE == "prod" and config.GMAIL_MCP_ENABLED:
        # Real Gmail MCP path (wired in WI-32). Imported lazily so the mock path
        # never requires the MCP dependencies.
        from utils.gmail_mcp import GmailMCPNotifier

        return GmailMCPNotifier()

    from tools import MockNotificationService

    return MockNotificationService()
