"""Central configuration — all thresholds, gates, and paths in one place.

Deterministic control flow (NFR-2) depends on these being explicit, typed
constants that conditional edges read — never magic numbers scattered in nodes.

Status: PLACEHOLDER — implemented in Phase 1 (WI-09).

Values to define here (sourced from the PRD, kept here for the Phase 1 author):
    Retries            MAX_RETRIES_PER_TOOL = 3           (FR-5)
    Backoff            RETRY_BACKOFF_SECONDS = (1, 3, 10) (recommended, §4.1)
    Confidence gates   AUTO_FIX_THRESHOLD = 0.85          (FR-4)
                       HITL_LOWER_THRESHOLD = 0.50        (FR-4)
    Severity rule      P0 never auto-resolves             (FR-4)
    Kill switch        MAX_TOTAL_STEPS = 20               (NFR-3)
    Paths              INCIDENTS_DIR, AUDIT_TRAIL_DIR, DLQ_DIR, CHECKPOINT_DB

Do not implement until Phase 1 begins (see docs/PHASES.md).
"""

# TODO(Phase 1, WI-09): define the constants documented above.
