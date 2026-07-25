# CLAUDE.md — Operating Guide for This Repository

Guidance for Claude Code (and any AI agent) working in this repo. Read this first,
every session. It encodes the PRD's rules and this project's process so the build
stays disciplined across all phases.

---

## 1. What this project is

An **Agentic On-Call Incident Response System**: a multi-agent LangGraph system
that acts as a first responder to production incidents. An alert comes in; the
agent investigates (logs, metrics, runbooks, recent deploys), forms a root-cause
hypothesis with a confidence score, and then **auto-fixes**, **pauses for human
review**, or **escalates** — logging every decision for post-mortems.

The engineering point is **not the happy path**. It is surviving tool failures,
avoiding runaway loops, logging every decision, pausing for human approval on
high-stakes actions, and resuming after a mid-run failure.

**Governing spec:** `Incident_Response_Agent_Documentation.pdf` (v1.0). Extracted
text is in `_prd_extracted.txt` (git-ignored scratch). When in doubt, the PDF wins.

## 2. Golden rules (do not break)

1. **Ask before deciding anything significant.** This is a hard requirement from
   the project lead. Before non-trivial or hard-to-reverse choices — anything
   touching a **Locked** item (§4.1), the state schema, external calls, or
   process — **stop and ask**. Prefer `AskUserQuestion` with concrete options.
   When unsure whether something is significant, treat it as significant.
2. **Locked architecture stays locked.** Three subgraphs (Diagnosis → Root Cause
   → Remediation) + supervisor; four novelty features; LangGraph + typed state;
   **OpenAI GPT-4o**; ≥1 real MCP tool (Gmail); semantic-version tags per phase;
   20+ test incidents. Changing any of these needs project-lead approval logged
   in `docs/PRD_CHANGES.md` + an ADR.
3. **Keep the docs live.** Every session, update `docs/` (see §6). Docs drifting
   from reality is a defect.
4. **One phase at a time.** No phase starts until the previous phase's release
   criteria in `docs/PHASES.md` all pass and its tag is cut.
5. **Never commit secrets.** `.env` is git-ignored; only `.env.example` is tracked.

## 3. Tech stack & commands

- **Python** 3.12 (≥3.11). **Package manager: uv.**
- **Stack:** LangGraph ≥0.2, LangChain ≥0.3, langchain-openai, Pydantic ≥2,
  LangSmith, langgraph-checkpoint-sqlite.

```bash
uv sync --extra dev          # create/refresh the venv from pyproject + lock
uv run python main.py --test-tools    # Phase 1+ CLI
uv run pytest                # run the test suite
uv run ruff check .          # lint
uv run mypy .                # type-check
```

> Env note: `uv sync` is deferred until Phase 1 begins (no code needs deps yet).

## 4. Repository layout (flat, matches PRD paths)

```
state/        IncidentState schema + AuditEvent/DeadLetterEntry + factory   (LOCKED contract)
tools/        Mock tools w/ injectable failures; real MCP tools later
utils/        failure_classifier · audit_trail · dead_letter_queue          (3 of 4 novelties)
agents/       diagnosis · root_cause · remediation · supervisor
evaluation/   run_eval · metrics
data/         incidents/ (inputs) · audit_trail/ · dlq/ (generated, git-ignored contents)
tests/        one test module per node/util; nodes tested in isolation first
config.py     all thresholds/gates/paths (deterministic control flow lives here)
main.py       CLI entry point
docs/         the project-tracking system — see docs/README.md
```

## 5. Coding standards (PRD §3.2 — enforced every PR)

- **Type hints** on every function signature. `mypy` must pass.
- **Docstrings on every node function** stating: what it **reads** from state,
  what it **writes**, and what **decision** it makes.
- **State discipline:** nodes return **only the fields they modify** — never the
  whole state object. No undocumented state fields; update `state/` + docs if the
  schema changes (and that change needs approval — the schema is locked at v0.1.0).
- **Audit completeness:** every node appends **exactly one** audit event before
  returning. No node exits without logging.
- **Deterministic routing (NFR-2):** conditional edges read explicit typed state
  fields (`retry_count`, `confidence`, `severity`) — never implicit LLM reasoning.
- **Testability:** every node testable in isolation **before** graph wiring; each
  subgraph passes its seed incidents **before** supervisor integration.

### The mandatory tool-calling node pattern (Phase 2+)
```
try:
    result = tool_call(...)
except Exception as e:
    failure_type = classify_failure(e)      # timeout|rate_limit|auth|malformed|unknown
    <update error state; select recovery strategy; max 3 retries, exp backoff>
    append_audit_event(...); return {<only changed fields>}
classification = classify_response(result)  # ok | empty (not error) | malformed (error)
<update data state>
append_audit_event(...); return {<only changed fields>}
```
**Graceful degradation (NFR-4):** if one data source fails but another succeeds,
proceed with partial data. Only route to failure handling if **all** sources fail.

## 6. Documentation protocol (do this continuously)

The `docs/` folder is maintained as you work — not at the end:

- **`docs/PHASES.md`** — flip work-item / release-criteria status (⬜🟨✅⛔) as it
  changes. This is the plan of record.
- **`docs/PROGRESS.md`** — add a dated entry each session: done / decisions /
  blockers / next step.
- **`docs/DECISIONS.md`** — record every non-trivial decision as an ADR (use the
  `log-decision` skill).
- **`docs/PRD_CHANGES.md`** — log any interpretation of or deviation from the PRD.
- **`docs/CHANGELOG.md`** — update per release (and for notable changes).
- **`docs/phases/`** — per-phase deep-dive notes when useful.

## 7. Phase-completion workflow (Git checkpoints)

Each phase ends with a tagged release. **Use the `phase-complete` skill** — it is
the authoritative checklist. In short: verify every release criterion → bump
version → update all docs → commit → `git tag vX.Y.Z`. Do **not** tag a phase with
unmet criteria; if something's incomplete, mark it ⏭️ in PHASES.md and get lead
sign-off first.

### Commit conventions
- **Conventional Commits:** `feat:`, `fix:`, `docs:`, `test:`, `refactor:`,
  `chore:`. Reference work items where relevant, e.g.
  `feat(state): add IncidentState schema (WI-01)`.
- Small, meaningful commits — the PRD requires "a clean git log with meaningful
  commit messages across all phases" (v1.0.0 release criterion).
- Every commit message ends with the required co-author trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- **Commit/push only when the phase workflow calls for it or the lead asks.**

## 8. When to stop and ask a human (non-exhaustive)

- Any change to a **Locked** item or the state schema.
- Confidence-gate / severity-rule threshold changes.
- Adding external side effects (sending real emails, real API calls, credentials).
- Ambiguity in the PRD that changes behavior.
- A release criterion can't be met — never quietly skip it.
- Anything you'd be unhappy to have a reviewer discover you decided alone.

When you pause, say clearly **what you need** and give **options with a
recommendation** — don't just ask an open question.
