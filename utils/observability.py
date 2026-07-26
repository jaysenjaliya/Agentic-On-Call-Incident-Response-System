"""LangSmith tracing integration (WI-31, NFR-1).

LangChain/LangGraph auto-instrument every LLM call, tool call, and node when two
env vars are present: ``LANGCHAIN_TRACING_V2=true`` and a valid ``LANGCHAIN_API_KEY``.
`config` already loads ``.env``, so tracing "just works" once a key is added — no
code changes. This module only reports status and builds per-run trace metadata.

To enable: put your LangSmith key in ``.env``::

    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=lsv2_...

Then every ``main.py <incident>`` run appears in the LangSmith dashboard under the
``LANGCHAIN_PROJECT`` project, one trace per incident.
"""

from __future__ import annotations

import os
from typing import Any

import config


def tracing_status() -> tuple[bool, str]:
    """Return ``(enabled, human_readable_detail)`` for the current environment.

    Enabled requires both the flag on AND a key present. If the flag is on but no
    key is set, tracing is inert (LangChain silently no-ops) — we say so, so it's
    obvious why no traces appear.
    """
    flag = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    has_key = bool(os.getenv("LANGCHAIN_API_KEY"))
    if flag and has_key:
        project = os.getenv("LANGCHAIN_PROJECT", config.PROJECT_ROOT.name)
        return True, f"enabled (project={project})"
    if flag and not has_key:
        return False, "flag on but LANGCHAIN_API_KEY missing — add it to .env to see traces"
    return False, "disabled (set LANGCHAIN_TRACING_V2=true + LANGCHAIN_API_KEY in .env)"


def run_config(incident_id: str, thread_id: str) -> dict[str, Any]:
    """Build the RunnableConfig for one incident invocation.

    Sets the ``thread_id`` (required by the checkpointer) and a human-friendly
    ``run_name`` + tags/metadata so each incident is easy to find in LangSmith.
    """
    return {
        "configurable": {"thread_id": thread_id},
        "run_name": f"incident:{incident_id}",
        "tags": ["incident-response", f"provider:{config.LLM_PROVIDER}"],
        "metadata": {"incident_id": incident_id, "llm_provider": config.LLM_PROVIDER},
    }
