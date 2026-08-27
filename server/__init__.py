"""HTTP deployment layer — serves the incident-response pipeline over a REST API.

This package is an *extension* on top of the locked v1.0.0 architecture (see
docs/PRD_CHANGES.md + docs/DECISIONS.md): it wraps the supervisor graph behind
FastAPI without modifying any locked component. The graph, state schema, tools,
and routing are untouched — the server only submits alerts, reads checkpointed
state, and applies HITL decisions exactly like the CLI does.
"""

from server.app import create_app

__all__ = ["create_app"]
