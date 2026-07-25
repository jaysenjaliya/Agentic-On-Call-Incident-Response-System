"""Utils package — cross-cutting production-grade machinery.

Houses three of the four mandatory novelty features (PRD §1.4):
    failure_classifier.py -- classify_failure() + classify_response()  (WI-06)
    audit_trail.py        -- append_audit_event / format_trail_for_human /
                             save_trail_to_file                        (WI-07)
    dead_letter_queue.py  -- send_to_dlq / review_dlq                  (WI-08)

Status: PLACEHOLDER — see docs/PHASES.md (Phase 1, WI-06..WI-08).
"""
