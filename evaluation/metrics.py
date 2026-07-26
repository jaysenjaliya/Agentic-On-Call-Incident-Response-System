"""Evaluation metrics (WI-36) — computes the portfolio metrics table (PRD §6.4).

Takes the list of per-incident result records from ``run_eval`` and computes:

    resolution_rate        auto-resolved / incidents that should resolve      (> 80%)
    escalation_precision   correct escalations / total escalations            (> 85%)
    escalation_recall      correct escalations / incidents needing escalation (> 90%)
    failure_recovery_rate  injected-failure runs that ended cleanly / total   (> 80%)
    audit_completeness     audit events logged / node executions (=steps)     (= 100%)
    dlq_capture_rate       unrecoverable runs captured to DLQ / total         (= 100%)
    avg_steps_to_resolution  mean steps over resolved incidents               (< 12)

Each metric is returned with its value, target, and whether it meets the target.
"""

from __future__ import annotations

from typing import Any

RESOLVED = "resolved"
ESCALATED = "escalated"
DEAD_LETTERED = "dead_lettered"


def _rate(numerator: int, denominator: int) -> float | None:
    """Return numerator/denominator, or ``None`` when the denominator is 0."""
    return round(numerator / denominator, 4) if denominator else None


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute all evaluation metrics from per-incident result records."""
    # Ground-truth partitions (by expected outcome / category).
    should_resolve = [r for r in results if r["expected_outcome"] == RESOLVED]
    should_escalate = [r for r in results if r["expected_outcome"] == ESCALATED]
    injected = [r for r in results if r["category"] == "tool_failure"]

    # Actual outcomes.
    resolved_correct = [r for r in should_resolve if r["actual_outcome"] == RESOLVED]
    actual_escalations = [r for r in results if r["actual_outcome"] == ESCALATED]
    escalations_correct = [r for r in actual_escalations if r["expected_outcome"] == ESCALATED]

    # Failure recovery: an injected-failure run is "handled" if it reached a valid
    # terminal state (resolved/escalated/dead_lettered) rather than crashing.
    terminal = {RESOLVED, ESCALATED, DEAD_LETTERED}
    handled = [r for r in injected if r["actual_outcome"] in terminal]

    # Audit completeness: every node both increments total_steps AND logs exactly
    # one event, so events/steps == 1.0 iff no node skipped logging.
    total_events = sum(r["audit_events"] for r in results)
    total_steps = sum(r["steps"] for r in results)

    # DLQ capture: of runs that should be unrecoverable (dead-lettered), how many
    # were actually captured to the DLQ. None are designed to in this suite.
    unrecoverable = [r for r in results if r["expected_outcome"] == DEAD_LETTERED]
    captured = [r for r in unrecoverable if r["dead_lettered"]]

    resolved_all = [r for r in results if r["actual_outcome"] == RESOLVED]
    avg_steps = (
        round(sum(r["steps"] for r in resolved_all) / len(resolved_all), 2)
        if resolved_all else None
    )

    def metric(value: float | None, target_txt: str, ok: bool | None) -> dict[str, Any]:
        return {"value": value, "target": target_txt, "pass": ok}

    def meets(value: float | None, threshold: float, *, minimum: bool = True) -> bool | None:
        if value is None:
            return None
        return value >= threshold if minimum else value <= threshold

    resolution_rate = _rate(len(resolved_correct), len(should_resolve))
    precision = _rate(len(escalations_correct), len(actual_escalations))
    recall = _rate(len(escalations_correct), len(should_escalate))
    recovery = _rate(len(handled), len(injected))
    audit = _rate(total_events, total_steps)
    dlq = _rate(len(captured), len(unrecoverable))

    return {
        "n_incidents": len(results),
        "counts": {
            "should_resolve": len(should_resolve),
            "should_escalate": len(should_escalate),
            "injected_failures": len(injected),
            "resolved_correct": len(resolved_correct),
            "actual_escalations": len(actual_escalations),
            "escalations_correct": len(escalations_correct),
        },
        "resolution_rate": metric(resolution_rate, "> 0.80", meets(resolution_rate, 0.80)),
        "escalation_precision": metric(precision, "> 0.85", meets(precision, 0.85)),
        "escalation_recall": metric(recall, "> 0.90", meets(recall, 0.90)),
        "failure_recovery_rate": metric(recovery, "> 0.80", meets(recovery, 0.80)),
        "audit_completeness": metric(audit, "= 1.00", None if audit is None else audit >= 1.0),
        "dlq_capture_rate": metric(
            dlq if dlq is not None else 1.0, "= 1.00 (0/0 n/a)",
            True if dlq is None else dlq >= 1.0,
        ),
        "avg_steps_to_resolution": metric(avg_steps, "< 12", meets(avg_steps, 12, minimum=False)),
    }


_METRIC_LABELS = [
    ("resolution_rate", "Resolution rate"),
    ("escalation_precision", "Escalation precision"),
    ("escalation_recall", "Escalation recall"),
    ("failure_recovery_rate", "Failure recovery rate"),
    ("audit_completeness", "Audit completeness"),
    ("dlq_capture_rate", "DLQ capture rate"),
    ("avg_steps_to_resolution", "Avg. steps to resolution"),
]


def format_metrics_table(metrics: dict[str, Any]) -> str:
    """Render the metrics as a Markdown table (used in the console + README)."""
    lines = [
        f"Evaluation over {metrics['n_incidents']} incidents:",
        "",
        "| Metric | Value | Target | Meets |",
        "|--------|-------|--------|-------|",
    ]
    for key, label in _METRIC_LABELS:
        m = metrics[key]
        val = m["value"]
        val_txt = "n/a" if val is None else (f"{val:.2f}" if val <= 1.0 else f"{val:.1f}")
        mark = "n/a" if m["pass"] is None else ("PASS" if m["pass"] else "MISS")
        lines.append(f"| {label} | {val_txt} | {m['target']} | {mark} |")
    return "\n".join(lines)
