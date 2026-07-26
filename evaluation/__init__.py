"""Evaluation package — the test harness that proves the system works.

Runs the synthetic incidents through the agent and computes the portfolio
metrics table (PRD §6.4).

Contents:
    run_eval.py  -- runs all incidents, collects results, writes results.json (WI-35)
    metrics.py   -- computes resolution rate, escalation precision/recall, failure
                    recovery rate, audit completeness, DLQ capture, avg steps (WI-36)
"""

from evaluation.metrics import compute_metrics, format_metrics_table

__all__ = ["compute_metrics", "format_metrics_table"]
