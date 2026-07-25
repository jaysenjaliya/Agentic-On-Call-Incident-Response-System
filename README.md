# Agentic On-Call Incident Response System

> Multi-agent LangGraph system with production-grade failure handling.
> **Status: Phase 0 (setup). The full portfolio README is a Phase 4 (`v1.0.0`) deliverable — this is a placeholder.**

An autonomous multi-agent system that acts as a **first responder to production
incidents**. When an alert fires, instead of immediately waking a human, the agent
investigates first — reading logs, checking metrics, searching past incidents,
identifying root causes — and then either fixes the problem automatically or wakes
the engineer with a fully prepared diagnosis and recommended action.

## Architecture (target)

Three specialized subgraphs coordinated by a supervisor:

```
Alert ─► [ Diagnosis ] ─► [ Root Cause ] ─► [ Remediation ] ─► Resolved | Escalated | Dead-lettered
             logs/metrics     runbooks/deploys    confidence-gated:
                                                  auto-fix · human review · escalate
```

Four production-readiness features run throughout:
1. **Adaptive failure classification** — tool errors classified semantically and
   routed to different recovery strategies (not a blanket retry counter).
2. **Confidence-gated human-in-the-loop** — the agent scores its own confidence
   and pauses for a human below threshold, presenting reasoning, not raw output.
3. **Dead letter queue** — unrecoverable runs serialize full state for later review.
4. **Audit trail as a first-class node** — every node appends a structured event.

## Tech stack

Python 3.12 · LangGraph · LangChain · **OpenAI GPT-4o** · Pydantic v2 · LangSmith ·
SQLite checkpointer · Gmail MCP (escalation) · uv · Git (semantic versioning).

## Quick start

```bash
uv sync --extra dev
cp .env.example .env         # add your OPENAI_API_KEY (and LangSmith key)
uv run python main.py --test-tools     # available from Phase 1
```

## Project documentation

Engineering log, phase plan, and decisions live in [`docs/`](docs/README.md).
Agent operating rules are in [`CLAUDE.md`](CLAUDE.md). Governing spec:
`Incident_Response_Agent_Documentation.pdf`.

---
*This README will be expanded in Phase 4 with the architecture diagram, evaluation
metrics table, demo output, and full setup instructions (PRD §3.3, WI-38).*
