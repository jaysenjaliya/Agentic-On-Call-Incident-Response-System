"""Shared pytest fixtures and global safety nets.

The autouse fixture here guarantees that **no test** ever spawns the Gmail MCP
server or sends a real email — regardless of what the developer's ``.env`` sets
(RUN_MODE/GMAIL_MCP_ENABLED). Tests that want to exercise escalation inject a
``MockNotificationService`` explicitly.
"""

from __future__ import annotations

import pytest

import config


@pytest.fixture(autouse=True)
def _force_mock_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force mock-only notifications for every test (no real Gmail / MCP spawns)."""
    monkeypatch.setattr(config, "RUN_MODE", "mock")
    monkeypatch.setattr(config, "GMAIL_MCP_ENABLED", False)
