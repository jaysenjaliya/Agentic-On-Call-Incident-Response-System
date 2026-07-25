"""Utils package — cross-cutting production-grade machinery.

Houses three of the four mandatory novelty features (PRD §1.4):
    failure_classifier -- classify_failure() + classify_response()
    audit_trail        -- append_audit_event / format_trail_for_human / save_trail_to_file
    dead_letter_queue  -- send_to_dlq / review_dlq
"""

from utils.audit_trail import (
    append_audit_event,
    format_trail_for_human,
    save_trail_to_file,
)
from utils.dead_letter_queue import review_dlq, send_to_dlq
from utils.failure_classifier import classify_failure, classify_response

__all__ = [
    "classify_failure",
    "classify_response",
    "append_audit_event",
    "format_trail_for_human",
    "save_trail_to_file",
    "send_to_dlq",
    "review_dlq",
]
