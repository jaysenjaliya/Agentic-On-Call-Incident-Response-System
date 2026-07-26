"""Real Gmail MCP notifier (WI-32) — the required real MCP tool (PRD §2.3, §4.1).

Connects to a Gmail MCP **server** over stdio (spawned via ``npx``) using
``langchain-mcp-adapters``, loads its tools, and calls the send-email tool to
dispatch a real escalation email. Selected by ``utils.notifier.get_notifier`` only
when ``RUN_MODE=prod`` and ``GMAIL_MCP_ENABLED=true``; otherwise the mock notifier
is used, so nothing external is ever sent by accident.

Setup is documented in ``docs/GMAIL_MCP_SETUP.md``. The server, command, and tool
name are configurable via env so you can swap MCP servers without code changes:

    GMAIL_MCP_COMMAND   default "npx"
    GMAIL_MCP_ARGS      default "-y @gongrzhe/server-gmail-autoauth-mcp"  (space-separated)
    GMAIL_MCP_SEND_TOOL default "send_email"

Failures raise; the ``escalate`` node catches them and still terminates the
incident (never stranded), logging the error in the audit trail.
"""

from __future__ import annotations

import asyncio
import os
import shlex
from typing import Any


class GmailMCPNotifier:
    """Sends escalation email through a Gmail MCP server. Sync ``.send`` facade."""

    def __init__(self) -> None:
        self.command = os.getenv("GMAIL_MCP_COMMAND", "npx")
        self.args = shlex.split(
            os.getenv("GMAIL_MCP_ARGS", "-y @gongrzhe/server-gmail-autoauth-mcp")
        )
        self.send_tool = os.getenv("GMAIL_MCP_SEND_TOOL", "send_email")

    async def _send_async(self, to: str, subject: str, body: str) -> Any:
        """Connect to the MCP server, find the send tool, and invoke it."""
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient({
            "gmail": {"command": self.command, "args": self.args, "transport": "stdio"}
        })
        tools = await client.get_tools()
        tool = next((t for t in tools if t.name == self.send_tool), None)
        if tool is None:
            available = ", ".join(t.name for t in tools)
            raise RuntimeError(
                f"Gmail MCP send tool {self.send_tool!r} not found. Available: {available}"
            )
        # gongrzhe's send_email expects a list of recipients.
        return await tool.ainvoke({"to": [to], "subject": subject, "body": body})

    def send(self, to: str, subject: str, body: str, channel: str = "gmail-mcp") -> dict[str, Any]:
        """Send a real email via Gmail MCP and return a receipt dict.

        Mirrors ``MockNotificationService.send`` so the escalate node is
        provider-agnostic. Runs the async MCP call to completion.
        """
        result = asyncio.run(self._send_async(to, subject, body))
        return {
            "status": "sent",
            "channel": channel,
            "to": to,
            "subject": subject,
            "result": str(result)[:300],
        }
