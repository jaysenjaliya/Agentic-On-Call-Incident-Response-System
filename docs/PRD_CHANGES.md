# PRD Deviations & Clarifications Log

The PRD (`Incident_Response_Agent_Documentation.pdf`, v1.0, July 2026) is the
governing spec. Some items are **Locked** (§4.1 — changeable only with
project-lead approval); others are **Flexible**. This file records every point
where our implementation **interprets, clarifies, or deviates** from the original
document — with the authorizing decision.

> Purpose: so a reviewer can diff "what the PRD said" against "what we built" and
> see exactly why any gap exists. Nothing changes silently.

| # | PRD reference | Type | What we did | Authorized by |
|---|---------------|------|-------------|---------------|
| C-01 | §2.3 Language: Python 3.11+ | Clarification | Targeting Python **3.12** (local runtime); satisfies the 3.11+ floor. | ADR-0003 |
| C-02 | §6 tooling implied pip/venv | Deviation (Flexible) | Using **uv** instead. Env management is not locked. | ADR-0003 |
| C-03 | Path references (`state/schemas.py`, `main.py`, …) | Clarification | Adopted a **flat package layout** matching these literal paths rather than a `src/` layout. File organization is Flexible (§4.1). | ADR-0005 |
| C-04 | §2.3 LangGraph ≥0.2.0, LangChain ≥0.3.0 | Clarification | Resolved to **LangGraph 1.2.9 / LangChain 1.3.14** (current majors). Both satisfy the `≥` floors; the PRD specifies minimums, not pins. | Phase 1 (WI env) |
| C-05 | §2.3/§4.1 **LLM provider = OpenAI** (Locked) | Deviation (temporary) | Running on **Groq** (`llama-3.3-70b-versatile`) while the OpenAI key is inactive. Hidden behind a provider abstraction; revert via `LLM_PROVIDER=openai`. | **Project lead** · ADR-0009 |
| C-06 | §2.3/§4.1 **model = GPT-4o** (Locked) | Deviation | OpenAI target model is **gpt-5-nano** (lead's choice), not gpt-4o. | **Project lead** · ADR-0009 |
| C-07 | v0.1.0 locked schema: `audit_trail: list[AuditEvent]` | Clarification (representation) | Stored as `list[dict]` (`AuditEvent.model_dump()`) for checkpoint/DLQ serializability; `AuditEvent` model retained as validator. | ADR-0010 |
| C-08 | §2.3 four mock tools | Addition (Flexible) | Added **MockMetricsAPI** (5th tool) for `pull_metrics`. §4.1 permits additional tools. | ADR-0011 |

---

## Locked items — confirmed unchanged

These are carried exactly as specified. Listed so their status is explicit:

- ✅ Three-subgraph architecture: Diagnosis → Root Cause → Remediation + supervisor.
- ✅ Four novelty features: adaptive failure classification, confidence-gated HITL,
  dead letter queue, audit trail.
- ✅ LangGraph orchestration with typed state.
- ⚠️ OpenAI as LLM provider — **temporarily Groq** (C-05, lead-approved) behind a
  one-line-switchable abstraction; OpenAI remains the target. Model is gpt-5-nano (C-06).
- ✅ ≥1 real MCP tool (Gmail) in production mode.
- ✅ Semantic versioning with tagged releases per phase.
- ✅ 20+ test incidents with documented evaluation metrics.

## How to log a new deviation

1. Add a row to the table with a new `C-NN` id and a one-line summary.
2. If it touches a **Locked** item, it needs explicit project-lead approval —
   record that approval and open a matching ADR in [DECISIONS.md](DECISIONS.md).
3. Note it in [PROGRESS.md](PROGRESS.md) for the session it happened.
