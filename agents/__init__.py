"""Agents package — the three subgraphs and the supervisor that orchestrates them.

Architecture is LOCKED (PRD §4.1): Diagnosis -> Root Cause -> Remediation,
coordinated by a supervisor.

Contents:
    diagnosis.py    -- pull_logs, pull_metrics, analyze_diagnosis,
                       handle_diagnosis_failure         (Phase 2, WI-11..WI-16)
    root_cause.py   -- search_runbooks, check_deployments,
                       analyze_root_cause               (Phase 2, WI-17..WI-21)
    remediation.py  -- evaluate_confidence, execute_fix, verify_fix,
                       human_review (HITL), escalate, close_incident
                                                        (Phase 2, WI-22..WI-27)
    supervisor.py   -- phase-based routing, kill switch, global error handling
                                                        (Phase 3, WI-28..WI-29)

Status: PLACEHOLDER — see docs/PHASES.md (Phases 2 & 3).
"""
