# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres to
[Semantic Versioning](https://semver.org/) with a tagged release at each phase
(PRD §6).

## [Unreleased]

_Optional Phase 5 stretch goals (trajectory summarization, self-healing supervisor)._

### Added (2026-08-27 — live server extension)
- FastAPI deployment layer (`server/`): submit alerts, poll status, HITL
  approve/reject, audit + DLQ endpoints over HTTP (ADR-0019, C-12).
- `deploy/` PowerShell scripts + `docs/DEPLOYMENT.md` for running the system as
  a LAN server on a second Windows PC; optional `SERVER_API_KEY` auth.
- `tests/test_server.py` (10 offline tests); `server` dependency extra.

### Changed
- Groq model default → `qwen/qwen3.8-27b` after upstream decommissioned
  `llama-3.3-70b-versatile` (ADR-0020).

## [v1.0.0] — 2026-07-26 — Phase 4: Evaluation & Documentation — **portfolio-ready**

The system evaluated at scale and packaged for the portfolio.

### Added
- **20 synthetic incidents** (`data/incidents/`): 10 auto-resolvable, 5 escalation,
  5 with injected tool failures — each labeled with category + expected outcome.
- **Fixture world** (`tools/fixtures.py`): per-service symptom logs/metrics/deploys
  so incidents are distinguishable; the three data tools read it by default.
- **Evaluation harness** (`evaluation/run_eval.py`): runs all 20 live, mock
  notifications, per-incident failure injection, rate-limit pacing, simulated HITL
  reviewer; writes `evaluation/results.json`.
- **Metrics** (`evaluation/metrics.py`): resolution rate, escalation precision/recall,
  failure-recovery rate, audit completeness, DLQ capture, avg steps + Markdown table.
- **Professional README**: overview, Mermaid architecture diagram, novelty table,
  evaluation table (with honest rate-limit note), setup, CLI/demo, tech stack.
- Tests: +9 evaluation tests → **157 total**.

### Changed
- Runbook search query uses deterministic signals (raw logs + alert), not LLM
  free-text — eliminates spurious matches on novel incidents (ADR-0016).
- LLM structured calls retry transient errors (rate limits) with backoff (ADR-0017).

### Evaluation
- Live run: 11/11 auto-resolve → resolved (conf 0.90); 5/5 escalations correct.
  recall/failure-recovery/audit/DLQ/avg-steps all meet target. Resolution 0.79 &
  precision 0.67 depressed by Groq free-tier token exhaustion degrading 3
  tool-failure incidents to safe escalation (C-11); a budget-available run met all 7
  targets. Shipped with a transparent caveat by project-lead decision.

### Release criteria
- All Phase 4 criteria in [PHASES.md](PHASES.md) verified ✅.

Git: tagged `v1.0.0` — the portfolio-ready release.

## [v0.3.0] — 2026-07-26 — Phase 3: Supervisor Integration & Production Hardening

The three subgraphs wired into one supervised pipeline with production features.
Verified live end-to-end (Groq + real Gmail MCP).

### Added
- **Supervisor pipeline** (`agents/supervisor.py`, WI-28): flat graph (Approach B)
  reusing Phase 2 nodes; kill switch (WI-29) → dead-letter on `total_steps` blow-out;
  `finalize` persists the audit trail every run.
- **SQLite checkpointer** (WI-30): crash recovery + HITL pause/resume; a fresh graph
  resumes a paused run from disk.
- **LangSmith tracing** (`utils/observability.py`, WI-31): env-driven; activates on
  adding a key.
- **Real Gmail MCP escalation** (`utils/notifier.py`, `utils/gmail_mcp.py`, WI-32):
  sends a real email via an MCP server; mock fallback when disabled. **Verified live.**
- **End-to-end CLI**: `python main.py <incident.json>` with `--hitl approve|reject`.
- Tests: +11 e2e (`test_supervisor.py`) → 148 total; `tests/conftest.py` guarantees
  no test sends real email.

### Changed
- `escalate` audit event now records the real notifier (`type(notifier).__name__`)
  and delivery channel instead of a hard-coded label (ADR-0014).

### Fixed
- Windows: MCP stdio servers launched via `cmd /c` (WinError 193) (ADR-0013).
- Test isolation: `.env` `RUN_MODE=prod` no longer causes tests to send real email.

### Security
- `.gitignore` now excludes Google OAuth/credential files (`gcp-oauth.keys*.json`,
  `credentials.json`, `.gmail-mcp/`). No secrets were ever committed.

### Release criteria
- All Phase 3 criteria in [PHASES.md](PHASES.md) verified ✅.

Git: tagged `v0.3.0`.

## [v0.2.0] — 2026-07-25 — Phase 2: Individual Subgraphs

Three subgraphs, each compiled and passing seed incidents independently, built on a
provider-agnostic LLM layer. Live-verified end-to-end on Groq.

### Added
- **Diagnosis subgraph** (`agents/diagnosis.py`, WI-11..16): pull_logs, pull_metrics,
  analyze_diagnosis (LLM + severity rubric), handle_diagnosis_failure; graceful
  degradation routing.
- **Root-cause subgraph** (`agents/root_cause.py`, WI-17..21): search_runbooks,
  check_deployments, analyze_root_cause (LLM + calibrated confidence).
- **Remediation subgraph** (`agents/remediation.py`, WI-22..27): confidence-gated
  three-branch routing (auto-fix / human-review / escalate), P0-never-auto-resolves,
  HITL checkpoint via LangGraph `interrupt_before` + MemorySaver, escalate/close.
- **LLM provider abstraction** (`utils/llm.py`, `LLM_PROVIDER` env): OpenAI or Groq,
  one-line switch.
- **Resilient tool loop** (`utils/tool_runner.py`): classify → retry w/ backoff (max
  3, auth non-retryable) → structured `ToolOutcome`; `agents/_common.apply_tool_outcome`.
- **MockMetricsAPI** (5th mock tool) for `pull_metrics`.
- Tests: +57 (137 total) — every node in isolation + compiled-graph + HITL + retry loop.

### Changed
- **LLM provider temporarily Groq** (`llama-3.3-70b-versatile`) while the OpenAI key
  is inactive; OpenAI (`gpt-5-nano`) remains the target (ADR-0009, C-05/C-06).
- **`audit_trail` now stores dicts** (`AuditEvent.model_dump()`) instead of model
  instances, for checkpoint/DLQ serializability (ADR-0010, C-07). Locked-schema
  representation change; `AuditEvent` retained as validator.
- `--test-tools` now exercises five tools; LangSmith tracing disabled until Phase 3.

### Release criteria
- All Phase 2 criteria in [PHASES.md](PHASES.md) verified ✅. Live chain: INC-001/002
  → resolved, INC-003 → escalated.

Git: tagged `v0.2.0`.

## [v0.1.0] — 2026-07-25 — Phase 1: Foundation

State schema, mock tools, and utilities — every unit tested in isolation. This is
the locked contract the rest of the system builds on.

### Added
- **State (WI-01):** `IncidentState` TypedDict (5 field categories, 42 fields),
  `AuditEvent` & `DeadLetterEntry` Pydantic models, `create_initial_state()`.
  `audit_trail` uses an `operator.add` reducer.
- **Config (WI-09):** `config.py` — retry/backoff (FR-5), kill switch
  `MAX_TOTAL_STEPS=20` (NFR-3), confidence gates `0.85`/`0.50` (FR-4), severity
  rules, failure/response/resolution taxonomies, and all runtime paths.
- **Failure classification (WI-06):** `classify_failure` +
  `classify_response` — novelty feature #1.
- **Mock tools (WI-02..05):** `MockLogAPI`, `MockRunbookSearch`, `MockGitHubAPI`,
  `MockNotificationService` with an injectable `FailureMode`
  (none/timeout/rate_limit/auth/empty/malformed) and a shared exception hierarchy.
- **Audit trail (WI-07):** `append_audit_event` / `format_trail_for_human` /
  `save_trail_to_file` — novelty feature #4.
- **Dead letter queue (WI-08):** `send_to_dlq` / `review_dlq` — novelty feature #3.
- **Seed incidents (WI-10):** INC-001 (resolve), INC-002 (resolve, different root
  cause), INC-003 (escalate).
- **CLI:** `main.py --test-tools | --test-state | --review-dlq`.
- **Tests:** 83 pytest unit tests; each unit tested in isolation.
- **Tooling:** `uv.lock`; ruff + mypy configured and passing on product code.

### Release criteria
- All Phase 1 criteria in [PHASES.md](PHASES.md) verified ✅ (evidence in
  [PROGRESS.md](PROGRESS.md)).

Git: tagged `v0.1.0`.

### Added (Phase 0 — pre-release scaffolding, shipped in the initial commit)
- Repository scaffolding, uv project config, flat package skeleton, documentation
  system (`docs/`), `CLAUDE.md`, and Claude Code skills (`phase-complete`,
  `log-decision`).

---

<!--
Release template — copy per phase when tagging:

## [vX.Y.Z] — YYYY-MM-DD — Phase N: <name>

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Release criteria
- All Phase N criteria in docs/PHASES.md verified ✅

Git: tagged `vX.Y.Z` at <commit sha>.
-->
