# Phase Plan & Live Status

> **The plan of record.** Update work-item and phase status here as work happens.
> Status legend: ⬜ Not started · 🟨 In progress · ✅ Done · ⛔ Blocked · ⏭️ Deferred/skipped

**Current phase:** Phase 0 — Project Setup (infrastructure & process) · **Latest tag:** _none yet_

| Version | Phase | Days | Milestone | Status |
|---------|-------|------|-----------|--------|
| — | 0 · Setup | — | Repo, docs system, CLAUDE.md + skills, uv env | 🟨 In progress |
| v0.1.0 | 1 · Foundation | 1–2 | State schema, tools, utilities — all tested | ⬜ |
| v0.2.0 | 2 · Subgraphs | 3–6 | Three subgraphs working independently | ⬜ |
| v0.3.0 | 3 · Integration | 7–9 | Full pipeline end-to-end + production features | ⬜ |
| v1.0.0 | 4 · Evaluation | 9–10 | Portfolio-ready with metrics + docs | ⬜ |
| v1.1.0 | 5 · Stretch | bonus | Trajectory summarization + self-healing supervisor | ⬜ |

**Critical path:** WI-01 → WI-11/17/22 → WI-15/20/26 → WI-28 → WI-33 → WI-38.

---

## Phase 0 — Project Setup (this session)

Not part of the PRD's numbered phases; establishes the scaffolding and the
process the PRD assumes. No product code.

- ✅ Read & extract the PRD
- ✅ Confirm key decisions with project lead (see DECISIONS.md ADR-0001..0004)
- ✅ `uv` installed; `pyproject.toml`, `.gitignore`, `.env.example`, `.python-version`
- ✅ Flat package skeleton (`state/ tools/ utils/ agents/ evaluation/`, `config.py`, `main.py`)
- ✅ Documentation system (`docs/`)
- ✅ `CLAUDE.md` + `.claude/skills/` (phase-complete, log-decision)
- ✅ `git init` (branch `main`) + initial commit `chore: bootstrap ...` (Phase 0). No tag — `v0.1.0` is cut at Phase 1 completion.
- ⏭️ Sync uv env / lockfile — deferred until Phase 1, to avoid resolving heavy LLM deps before any code runs.

**Exit → Phase 1** when: project lead reviews the setup. Repo initialized ✅, first commit made ✅.

---

## Phase 1 — Foundation · `v0.1.0` · Days 1–2

**Goal:** state schema, mock tools, and utilities — every piece unit-tested in
isolation. This is the locked contract the rest of the system builds on.

| WI | Work item | Prio | Est | Depends | Status |
|----|-----------|------|-----|---------|--------|
| WI-01 | Define `IncidentState` schema (5 field categories) + `AuditEvent`, `DeadLetterEntry`, `create_initial_state()` | P0 | 0.5d | — | ⬜ |
| WI-02 | `MockLogAPI` with 4 failure modes | P0 | 0.5d | WI-01 | ⬜ |
| WI-03 | `MockRunbookSearch` (keyword matching) | P0 | 0.5d | WI-01 | ⬜ |
| WI-04 | `MockGitHubAPI` (deployment history) | P0 | 0.5d | WI-01 | ⬜ |
| WI-05 | `MockNotificationService` | P0 | 0.25d | WI-01 | ⬜ |
| WI-06 | Failure classifier (`classify_failure` + `classify_response`) | P0 | 0.5d | — | ⬜ |
| WI-07 | Audit trail util (append / format / save) | P0 | 0.5d | WI-01 | ⬜ |
| WI-08 | Dead letter queue util (send / review) | P0 | 0.5d | WI-01 | ⬜ |
| WI-09 | `config.py` with all thresholds | P0 | 0.25d | — | ⬜ |
| WI-10 | 3 seed test incidents (JSON) | P0 | 0.25d | — | ⬜ |

**Release criteria for v0.1.0** (all must pass):
- ⬜ `main.py --test-tools` — 4 tools work; all failure modes raise correct exceptions
- ⬜ `main.py --test-state` — state creation works; all fields present w/ correct defaults
- ⬜ `classify_failure` maps: `TimeoutError`→timeout, 429→rate_limit, 401→auth, unknown→unknown
- ⬜ `classify_response` distinguishes: ok, empty (not error), malformed (is error)
- ⬜ Audit trail appends, formats, and saves to file
- ⬜ DLQ writes and reads JSON files
- ⬜ Git tag `v0.1.0` created

---

## Phase 2 — Individual Subgraphs · `v0.2.0` · Days 3–6

**Goal:** three subgraphs, each compiled and passing seed incidents
**independently** before any supervisor wiring. Buildable in parallel — they
share only the locked v0.1.0 state schema.

**Tool-calling node pattern (mandatory):** `try tool call → on exception:
classify_failure() → update error state → audit → return`; on success:
`classify_response() → update data state → audit → return`. Max 3 retries,
exponential backoff. See `.claude/skills/` for the node-authoring guidance.

### Stream A — Diagnosis (`agents/diagnosis.py`)
| WI | Work item | Prio | Est | Depends | Status |
|----|-----------|------|-----|---------|--------|
| WI-11 | `pull_logs` node w/ failure handling | P0 | 0.5d | WI-02, WI-06 | ⬜ |
| WI-12 | `pull_metrics` node w/ failure handling | P0 | 0.5d | WI-02, WI-06 | ⬜ |
| WI-13 | `analyze_diagnosis` node (LLM call) | P0 | 1d | WI-11, WI-12 | ⬜ |
| WI-14 | `handle_diagnosis_failure` node | P0 | 0.5d | WI-06, WI-08 | ⬜ |
| WI-15 | Wire diagnosis subgraph (conditional edges) | P0 | 0.5d | WI-11..14 | ⬜ |
| WI-16 | Test diagnosis subgraph in isolation | P0 | 0.5d | WI-15 | ⬜ |

### Stream B — Root Cause (`agents/root_cause.py`)
| WI | Work item | Prio | Est | Depends | Status |
|----|-----------|------|-----|---------|--------|
| WI-17 | `search_runbooks` node w/ failure handling | P0 | 0.5d | WI-03, WI-06 | ⬜ |
| WI-18 | `check_deployments` node w/ failure handling | P0 | 0.5d | WI-04, WI-06 | ⬜ |
| WI-19 | `analyze_root_cause` node (LLM call) | P0 | 1d | WI-17, WI-18 | ⬜ |
| WI-20 | Wire root cause subgraph (conditional edges) | P0 | 0.5d | WI-17..19 | ⬜ |
| WI-21 | Test root cause subgraph in isolation | P0 | 0.5d | WI-20 | ⬜ |

### Stream C — Remediation (`agents/remediation.py`)
| WI | Work item | Prio | Est | Depends | Status |
|----|-----------|------|-----|---------|--------|
| WI-22 | `evaluate_confidence` decision node (reads confidence **and** severity) | P0 | 0.5d | WI-09 | ⬜ |
| WI-23 | `execute_fix` and `verify_fix` nodes | P0 | 1d | WI-22 | ⬜ |
| WI-24 | `human_review` HITL checkpoint node | P0 | 1d | WI-22 | ⬜ |
| WI-25 | `escalate` and `close_incident` nodes | P0 | 0.5d | WI-05, WI-07 | ⬜ |
| WI-26 | Wire remediation subgraph (3-branch routing) | P0 | 1d | WI-22..25 | ⬜ |
| WI-27 | Test remediation subgraph — all 3 branches | P0 | 0.5d | WI-26 | ⬜ |

**Release criteria for v0.2.0:**
- ⬜ Each subgraph compiles & runs independently against seed incidents
- ⬜ Diagnosis produces `diagnosis_summary` + `severity` for incident_001
- ⬜ Root cause produces `root_cause_hypothesis` + `confidence` for incident_001
- ⬜ Remediation routes: high confidence → auto-fix, low → escalate
- ⬜ Tool-failure injection (timeout) triggers classification + retry, not a crash
- ⬜ Audit trail contains entries from every node that executed
- ⬜ Git tag `v0.2.0` created

---

## Phase 3 — Supervisor Integration & Production Hardening · `v0.3.0` · Days 7–9

**Goal:** wire the three subgraphs into one pipeline and add the production
features. **Approach B first** (flat graph, `current_phase` routing — faster to
build/debug); refactor to Approach A (compiled subgraphs as nodes) only if time
permits.

| WI | Work item | Prio | Est | Depends | Status |
|----|-----------|------|-----|---------|--------|
| WI-28 | Supervisor graph wiring 3 subgraphs | P0 | 1d | WI-16, 21, 27 | ⬜ |
| WI-29 | Kill switch node (`MAX_TOTAL_STEPS`) | P0 | 0.25d | WI-28 | ⬜ |
| WI-30 | SQLite checkpointer (crash recovery + HITL pause/resume) | P1 | 0.5d | WI-28 | ⬜ |
| WI-31 | Enable LangSmith tracing | P1 | 0.5d | WI-28 | ⬜ |
| WI-32 | Gmail MCP integration (real escalation emails; mock fallback) | P1 | 1d | WI-25 | ⬜ |
| WI-33 | End-to-end test: all 3 seed incidents | P0 | 0.5d | WI-28..32 | ⬜ |

**Release criteria for v0.3.0:**
- ⬜ `main.py` runs incident_001 end-to-end: alert → diagnosis → root cause → auto-fix → resolved
- ⬜ incident_003 routes to escalation — `human_review` HITL checkpoint fires
- ⬜ Kill switch triggers when `total_steps > 20` → DLQ, not infinite loop
- ⬜ Tool-failure injection does not crash the pipeline
- ⬜ LangSmith trace shows full node-by-node execution for ≥1 incident
- ⬜ Gmail MCP sends a real email on escalation (or documented mock fallback)
- ⬜ Audit trail files generated in `data/audit_trail/` for every run
- ⬜ Git tag `v0.3.0` created

---

## Phase 4 — Evaluation & Documentation · `v1.0.0` · Days 9–10

**Goal:** prove it works at scale and package it for the portfolio. **This is the
portfolio-ready release.**

| WI | Work item | Prio | Est | Depends | Status |
|----|-----------|------|-----|---------|--------|
| WI-34 | 17 additional synthetic incidents (→ 20 total) | P1 | 1d | WI-10 | ⬜ |
| WI-35 | `evaluation/run_eval.py` (runs all 20) | P1 | 1d | WI-33 | ⬜ |
| WI-36 | `evaluation/metrics.py` (compute metrics) | P1 | 0.5d | WI-35 | ⬜ |
| WI-37 | Run full evaluation, document results | P1 | 0.5d | WI-36 | ⬜ |
| WI-38 | Professional README with all sections | P0 | 1d | WI-37 | ⬜ |

**Incident mix:** 10 auto-resolvable · 5 escalation-required · 5 with injected tool failures.

**Metrics + targets:** resolution rate >80% · escalation precision >85% · escalation
recall >90% · failure recovery >80% · audit completeness 100% · DLQ capture 100% ·
avg steps to resolution <12.

**Release criteria for v1.0.0:**
- ⬜ 20 incidents run through the agent, results logged
- ⬜ All metrics computed and documented in README
- ⬜ README has all sections (architecture, novelty, evaluation, demo, setup)
- ⬜ Clean git log with meaningful commit messages across all phases
- ⬜ Git tag `v1.0.0` created

---

## Phase 5 — Stretch Goals · `v1.1.0` · Bonus

| WI | Work item | Prio | Est | Depends | Status |
|----|-----------|------|-----|---------|--------|
| WI-39 | Trajectory summarization node (every N steps, default 5) | P2 | 1.5d | WI-28 | ⬜ |
| WI-40 | Self-healing supervisor (health metrics → fallback path) | P3 | 2d | WI-28 | ⬜ |

**Release criteria for v1.1.0:**
- ⬜ Stretch features work without breaking any v1.0.0 functionality
- ⬜ README documents the stretch features
- ⬜ Git tag `v1.1.0` created
