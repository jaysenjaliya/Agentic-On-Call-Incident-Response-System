"""Central configuration — all thresholds, gates, severity rules, and paths.

Deterministic control flow (NFR-2) depends on these being explicit, typed
constants that conditional edges read — never magic numbers scattered in nodes.
Everything the routing logic keys on lives here so it can be reasoned about and
tuned in one place.

Sourced from the PRD (FR-4, FR-5, NFR-3, §6.1). Implemented in Phase 1 (WI-09).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Resolve everything relative to this file so the CLI works from any cwd.
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# Load .env as early as possible so every os.getenv() below sees real values,
# regardless of which entrypoint imported config first. Idempotent; does not
# override variables already set in the real environment.
load_dotenv(PROJECT_ROOT / ".env")
DATA_DIR: Path = PROJECT_ROOT / "data"
INCIDENTS_DIR: Path = DATA_DIR / "incidents"
AUDIT_TRAIL_DIR: Path = DATA_DIR / "audit_trail"
DLQ_DIR: Path = DATA_DIR / "dlq"

# SQLite checkpointer DB (used from Phase 3 onward; declared here for one source).
CHECKPOINT_DB: Path = PROJECT_ROOT / "checkpoints" / "incident_checkpoints.sqlite"


# ---------------------------------------------------------------------------
# Retry / failure handling (FR-5)
# ---------------------------------------------------------------------------
# "Maximum 3 retries per tool with exponential backoff."
MAX_RETRIES_PER_TOOL: int = 3

# Recommended backoff schedule (§4.1 — a recommendation, not a mandate).
# Indexed by attempt number: 1st retry waits 1s, 2nd 3s, 3rd 10s.
RETRY_BACKOFF_SECONDS: tuple[int, ...] = (1, 3, 10)


# ---------------------------------------------------------------------------
# Runaway-loop protection (NFR-3)
# ---------------------------------------------------------------------------
# Global kill switch: any run exceeding this many total steps is terminated and
# routed to the dead letter queue with full state preserved.
MAX_TOTAL_STEPS: int = 20


# ---------------------------------------------------------------------------
# Confidence gating (FR-4)
# ---------------------------------------------------------------------------
# confidence > AUTO_FIX_THRESHOLD (and severity != P0) -> auto-remediate.
# HITL_LOWER_THRESHOLD <= confidence <= AUTO_FIX_THRESHOLD -> human review.
# confidence < HITL_LOWER_THRESHOLD (or severity == P0)  -> escalate immediately.
AUTO_FIX_THRESHOLD: float = 0.85
HITL_LOWER_THRESHOLD: float = 0.50


# ---------------------------------------------------------------------------
# Severity rules (FR-2, FR-4)
# ---------------------------------------------------------------------------
# Valid severity classifications, ordered most-to-least severe.
SEVERITY_LEVELS: tuple[str, ...] = ("P0", "P1", "P2", "P3")

# Severities that must NEVER auto-resolve regardless of confidence (FR-4).
NO_AUTO_RESOLVE_SEVERITIES: frozenset[str] = frozenset({"P0"})

# Default severity applied at state initialization before diagnosis runs.
DEFAULT_SEVERITY: str = "P3"


# ---------------------------------------------------------------------------
# Terminal resolution states (FR-9)
# ---------------------------------------------------------------------------
# Every incident must terminate in exactly one of these — none silently dropped.
RESOLUTION_RESOLVED: str = "resolved"
RESOLUTION_ESCALATED: str = "escalated"
RESOLUTION_DEAD_LETTERED: str = "dead_lettered"
RESOLUTION_STATES: tuple[str, ...] = (
    RESOLUTION_RESOLVED,
    RESOLUTION_ESCALATED,
    RESOLUTION_DEAD_LETTERED,
)


# ---------------------------------------------------------------------------
# Failure classification taxonomy (FR-5)
# ---------------------------------------------------------------------------
# Semantic failure types the classifier maps exceptions to. Each maps to a
# distinct recovery strategy (used from Phase 2 in the tool-calling nodes).
FAILURE_TIMEOUT: str = "timeout"
FAILURE_RATE_LIMIT: str = "rate_limit"
FAILURE_AUTH: str = "auth"
FAILURE_MALFORMED: str = "malformed"
FAILURE_UNKNOWN: str = "unknown"
FAILURE_TYPES: tuple[str, ...] = (
    FAILURE_TIMEOUT,
    FAILURE_RATE_LIMIT,
    FAILURE_AUTH,
    FAILURE_MALFORMED,
    FAILURE_UNKNOWN,
)

# Response classifications from classify_response(). "empty" is explicitly NOT an
# error (a valid "no data" result); "malformed" IS an error.
RESPONSE_OK: str = "ok"
RESPONSE_EMPTY: str = "empty"
RESPONSE_MALFORMED: str = "malformed"


# ---------------------------------------------------------------------------
# LLM provider. Target is OpenAI (locked, ADR-0001); "groq" is a temporary,
# OpenAI-compatible fallback while the OpenAI key is inactive (ADR-0009).
# Switching providers is a one-line change: set LLM_PROVIDER in .env.
# ---------------------------------------------------------------------------
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()

# OpenAI (target provider).
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-nano")

# Groq (temporary provider). OpenAI-compatible API serving open models.
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Deterministic-leaning outputs for reproducible diagnoses/evaluation.
LLM_TEMPERATURE: float = 0.0


# ---------------------------------------------------------------------------
# Runtime mode / notifications (Phase 3)
# ---------------------------------------------------------------------------
# "mock" -> MockNotificationService only; "prod" -> real MCP tools where set up.
RUN_MODE: str = os.getenv("RUN_MODE", "mock")
GMAIL_MCP_ENABLED: bool = os.getenv("GMAIL_MCP_ENABLED", "false").lower() == "true"
ESCALATION_EMAIL_TO: str = os.getenv("ESCALATION_EMAIL_TO", "oncall@example.com")


def ensure_runtime_dirs() -> None:
    """Create the directories the agent writes to at runtime, if missing.

    Safe to call repeatedly. Keeps generated-output paths in one place so nodes
    never have to worry about directory existence.
    """
    for directory in (INCIDENTS_DIR, AUDIT_TRAIL_DIR, DLQ_DIR, CHECKPOINT_DB.parent):
        directory.mkdir(parents=True, exist_ok=True)
