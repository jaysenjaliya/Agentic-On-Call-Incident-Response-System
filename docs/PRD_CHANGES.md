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
| C-09 | §6.3 "Enable LangSmith tracing" | Clarification | Tracing is **integrated and env-driven** (auto-activates when `LANGCHAIN_API_KEY` is set); left inert pending the lead adding a key. Criterion met as documented setup. | Project lead (Phase 3 Q) |
| C-10 | §6.3 "incident_003 … human_review HITL checkpoint fires" | Clarification | INC-003 is P0 → escalates immediately (FR-4: P0 never auto-resolves), so it does **not** pass through `human_review`. HITL firing + pause/resume is demonstrated for mid-confidence (0.50–0.85) runs instead (supervisor tests + CLI `--hitl`). | ADR-0012 |
| C-11 | §6.4 evaluation metrics targets | Caveat (environmental) | The live eval ran on Groq's **free tier**; its daily/per-minute token budget was exhausted by a day of testing, degrading 3 tool-failure incidents to safe escalation. This depresses *resolution rate* (0.79) and *escalation precision* (0.67) only; a budget-available run met all 7 targets (resolution 0.93, precision 0.86). Shipped with a transparent README note by **project-lead decision** rather than waiting for reset. | Project lead |
| C-12 | PRD scope: CLI entry point only (§3, §6) | Addition (post-v1.0.0 extension) | Added an **HTTP deployment layer** (`server/` FastAPI app + `deploy/` scripts + `docs/DEPLOYMENT.md`) so the system runs as a live LAN server on a second PC. Pure wrapper — no locked component modified; graph/state/tools/routing untouched. Groq model also swapped after upstream decommission (`qwen/qwen3.8-27b`). Live runs may inject tool failures per request (`inject_failures`), mirroring the evaluation harness's chaos switch; `GET /` redirects to the API docs. | ADR-0019, ADR-0020, ADR-0021, ADR-0022 |

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
