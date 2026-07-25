"""State package — the shared, typed contract for the whole system.

Owns the ``IncidentState`` schema that every subgraph reads from and writes to.
This schema is LOCKED at v0.1.0 (PRD §4.1): no subgraph may add fields without
updating this package and the state documentation.

Contents (implemented in Phase 1 — Foundation):
    schemas.py  -- IncidentState (TypedDict), AuditEvent (Pydantic),
                   DeadLetterEntry (Pydantic), create_initial_state() factory.

Status: PLACEHOLDER — see docs/PHASES.md (Phase 1, WI-01).
"""
