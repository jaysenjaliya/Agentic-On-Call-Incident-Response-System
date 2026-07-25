"""State package — the shared, typed contract for the whole system.

Owns the ``IncidentState`` schema that every subgraph reads from and writes to.
This schema is LOCKED at v0.1.0 (PRD §4.1): no subgraph may add fields without
updating this package and getting project-lead approval.
"""

from state.schemas import (
    AuditEvent,
    DeadLetterEntry,
    IncidentState,
    create_initial_state,
)

__all__ = [
    "IncidentState",
    "AuditEvent",
    "DeadLetterEntry",
    "create_initial_state",
]
