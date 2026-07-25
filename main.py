"""CLI entry point for the Agentic Incident Response System.

Planned commands (built across phases — see docs/PHASES.md):
    Phase 1 (WI):  --test-tools    exercise all mock tools + failure modes
                   --test-state    verify state creation & defaults
                   --review-dlq    print dead-letter-queue contents
    Phase 3+:      <incident.json> run one incident end-to-end through the graph

Status: PLACEHOLDER — implemented starting Phase 1 (Foundation).
"""


def main() -> None:
    """Dispatch CLI commands. Not yet implemented — scaffolding only."""
    raise NotImplementedError(
        "CLI not implemented yet. This is the v0.1.0 scaffolding checkpoint; "
        "see docs/PHASES.md for the Phase 1 plan."
    )


if __name__ == "__main__":
    main()
