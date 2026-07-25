# Documentation & Project-Tracking System

This folder is the **single source of truth** for how the Agentic Incident
Response System is being built. It is maintained continuously as work
progresses — not written once and abandoned.

> The product README (architecture, metrics, demo) lives at the repo root and is
> a **Phase 4** deliverable. *This* folder is the internal engineering log.

## The documents

| File | Purpose | Update cadence |
|------|---------|----------------|
| [PHASES.md](PHASES.md) | The 5-phase plan with every work item, release criteria, and live status. **The plan of record.** | Whenever a work item / phase changes status |
| [PROGRESS.md](PROGRESS.md) | Chronological worklog — what was done each session, decisions taken, blockers, next steps. | Every working session |
| [CHANGELOG.md](CHANGELOG.md) | Release-facing changelog (Keep a Changelog format), one section per version tag. | Every phase release + notable change |
| [DECISIONS.md](DECISIONS.md) | Architecture Decision Records — *why* each significant choice was made, with alternatives. | When a non-trivial decision is made |
| [PRD_CHANGES.md](PRD_CHANGES.md) | Log of any deviation from the original PRD, plus the approval that authorized it. | When the spec is interpreted, deviated from, or clarified |
| [phases/](phases/) | Per-phase deep-dive notes (design, gotchas, test evidence) as each phase runs. | During each phase |

## How these connect to Git

Each phase ends with a tagged release (`v0.1.0` → `v1.0.0`), per PRD §6. The
`phase-complete` skill (`.claude/skills/phase-complete/`) defines the exact
checklist Claude Code runs at every phase boundary: verify release criteria →
update these docs → commit → tag. See [../CLAUDE.md](../CLAUDE.md).

## Reading order for a newcomer

1. Root `README.md` (once it exists) — what the system does.
2. [PHASES.md](PHASES.md) — where we are and what's next.
3. [DECISIONS.md](DECISIONS.md) — why the system looks the way it does.
4. [PROGRESS.md](PROGRESS.md) — the detailed history.
