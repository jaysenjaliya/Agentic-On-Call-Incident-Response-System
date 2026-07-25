"""Dead letter queue — novelty feature #3 (PRD §1.4, FR-7).

When a run fails beyond recovery (all retries exhausted, or the kill switch fires),
its full state snapshot is serialized here so nothing is silently lost — available
for later human review or automated retry (FR-9: no incident silently dropped).

Two helpers:
    send_to_dlq(state, reason)  -- serialize a failed run to data/dlq/ as JSON.
    review_dlq()                -- load all DLQ entries back for inspection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config
from state.schemas import DeadLetterEntry, IncidentState


def _serialize_state(state: IncidentState) -> dict[str, Any]:
    """Return a JSON-safe copy of the state.

    Every field in ``IncidentState`` is JSON-native (audit events are stored as
    dicts, not model instances), so a shallow copy suffices. Kept as a seam in
    case future fields need conversion.
    """
    return dict(state)


def send_to_dlq(
    state: IncidentState,
    reason: str,
    *,
    failure_type: str | None = None,
    directory: Path | None = None,
) -> Path:
    """Serialize a failed run to the dead letter queue and return the file path.

    Reads the whole state; writes ``<incident_id>_dlq.json`` under ``data/dlq/``.
    ``reason`` explains why the run was dead-lettered (e.g. "max_steps_exceeded",
    "all_data_sources_failed"). ``failure_type`` defaults to the state's last
    classified failure.
    """
    target_dir = directory if directory is not None else config.DLQ_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    entry = DeadLetterEntry(
        incident_id=state["incident_id"],
        reason=reason,
        failure_type=failure_type if failure_type is not None else state.get("last_failure_type"),
        last_error=state.get("last_error"),
        total_steps=state.get("total_steps", 0),
        state_snapshot=_serialize_state(state),
    )

    path = target_dir / f"{state['incident_id']}_dlq.json"
    path.write_text(json.dumps(entry.model_dump(), indent=2), encoding="utf-8")
    return path


def review_dlq(directory: Path | None = None) -> list[DeadLetterEntry]:
    """Load all dead-letter entries from ``data/dlq/`` (newest first).

    Reads every ``*_dlq.json`` file; returns parsed ``DeadLetterEntry`` objects,
    sorted by timestamp descending. Returns ``[]`` if the directory is empty or
    absent — a clean, no-error result.
    """
    target_dir = directory if directory is not None else config.DLQ_DIR
    if not target_dir.exists():
        return []

    entries: list[DeadLetterEntry] = []
    for path in sorted(target_dir.glob("*_dlq.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries.append(DeadLetterEntry.model_validate(raw))

    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries
