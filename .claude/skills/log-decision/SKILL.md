---
name: log-decision
description: Record a significant engineering or product decision as an Architecture Decision Record (ADR) in docs/DECISIONS.md. Use whenever a non-trivial choice is made — architecture, dependencies, schema, thresholds, deviations from the PRD, or a decision the project lead confirmed. Keeps a durable, reviewable trail of why the system looks the way it does.
---

# Log a Decision (ADR)

Significant decisions must be captured so a reviewer can reconstruct *why*. Do
this at the moment the decision is made — not retroactively from memory.

## When to log
- Any choice touching a **Locked** PRD item (§4.1) — always, with the approval.
- Architecture, framework, or dependency choices.
- State-schema shape or threshold/gate values.
- A deviation from or interpretation of the PRD (also add a row to
  `docs/PRD_CHANGES.md`).
- Anything you paused to ask the project lead about — record their answer.

If it's not worth an ADR but still noteworthy, a line in `docs/PROGRESS.md` is enough.

## How to write it
1. Open `docs/DECISIONS.md`. Find the highest existing `ADR-NNNN` and use the next
   number (zero-padded, sequential, append at the bottom).
2. Add an entry in this exact shape:

```
## ADR-NNNN — <short imperative title>
- **Date:** YYYY-MM-DD · **Status:** Accepted · **Decider:** <who>
- **Context:** <the situation and forces; why a decision was needed>
- **Decision:** <what was chosen, stated plainly>
- **Alternatives:** <options considered and why rejected>
- **Consequences:** <what this makes easier/harder; follow-ups; risks>
```

3. **Status** starts `Proposed` if unconfirmed, `Accepted` once decided. To
   reverse a past ADR, don't delete it — mark the old one
   `Superseded by ADR-NNNN` and write the new one.
4. If it deviates from the PRD, add/UPDATE the matching `C-NN` row in
   `docs/PRD_CHANGES.md` and cross-reference the ADR.
5. Note the decision in the current `docs/PROGRESS.md` session entry.

## Quality bar
- Title is a decision, not a topic: "Use SQLite checkpointer for HITL resume,"
  not "Checkpointing."
- Record the road *not* taken — the alternatives are the most useful part later.
- One decision per ADR.
