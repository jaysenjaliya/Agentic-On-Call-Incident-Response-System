# Progress Log

Reverse-chronological worklog. Newest entry on top. Each working session gets an
entry: what was done, decisions, blockers, and the next step. Dates are absolute.

---

## 2026-08-28 — Live server hardening: chaos injection, battery runner, root redirect

**Done** — server deployed on the spare PC (10.200.10.201:8000) and driving
incidents; this session made it demonstrate the system's actual engineering point.

- **Reachability blocker found**: the server is unreachable from the dev PC —
  ping and TCP:8000 both fail. Dev PC is 10.200.17.108, server 10.200.10.201:
  different /24s on an institutional network, i.e. client isolation, not a
  firewall. Lead's fix: put **both PCs on a phone hotspot**. Troubleshooting
  section in DEPLOYMENT.md rewritten to diagnose this first.
- **Gap found + closed (ADR-0021)**: the seeded tool-failure incidents
  (INC-016..020) carry `inject_failures`, but the server ignored it — the five
  resilience incidents ran as happy-path. `POST /incidents` now accepts a
  validated `inject_failures` map and compiles a per-incident graph with the
  failing tools, sharing the one checkpointer so HITL pause/resume still works.
  Added `data_sources_failed` + `matched_runbook_id` to the status payload.
- **`deploy/run_demo_battery.ps1`**: submits seeded incidents over HTTP, answers
  the HITL checkpoint (default policy mirrors ADR-0018), scores against
  `expected_outcome`, prints a table, saves JSON. Refuses to run against a
  `run_mode=prod` server unless `-AllowProd` (would send real emails).
- **`GET /` redirects to `/docs`** (ADR-0022) — the bare URL used to 404.
- **Verified live over HTTP** (real Groq LLM): INC-001 resolved (0.92, 11 steps);
  INC-003/013 escalated; INC-016 `{metrics:timeout}` → degraded gracefully to
  **resolved**; INC-018 `{runbooks:timeout}` → confidence 0.7 → **HITL pause** →
  reject → **escalated**. 5/5 matched expected outcomes.
- Suite 173 passed (16 server tests); ruff + mypy clean on `server/`.

**Decisions** — ADR-0021 (per-request failure injection), ADR-0022 (root → /docs).
Both confirmed with the lead via AskUserQuestion; PRD_CHANGES C-12 extended.

**Blockers** — none in code. Network reachability is a physical fix (hotspot).

**Next** — on the hotspot, restart the server, then from the dev PC run
`deployun_demo_battery.ps1 -Server http://<new-ip>:8000 -All` to capture a
full 20-incident live run.

---

## 2026-08-27 — Live LAN server deployment layer (post-v1.0.0 extension)

**Done** — the system now runs as a real HTTP server on a spare Windows PC.

- **`server/app.py`** (FastAPI, ADR-0019): wraps the unchanged v1.0.0 supervisor
  graph — `POST /incidents` (202 + background run on a 2-worker pool, SQLite
  checkpointer), `GET /incidents/{id}` polling, `POST /incidents/{id}/hitl`
  approve/reject over HTTP, `/audit`, `/dlq`, `/health`, optional
  `SERVER_API_KEY` → `X-API-Key` gate. Status of pre-restart incidents is
  recovered from the checkpoint DB.
- **`deploy/`**: `setup_server.ps1` (uv install + sync + .env scaffold + offline
  smoke checks), `run_server.ps1` (firewall rule, LAN URLs, uvicorn),
  `send_test_incident.ps1` (client-side end-to-end driver). Guide:
  `docs/DEPLOYMENT.md`.
- **Tests**: `tests/test_server.py` — 10 offline tests (stub-LLM graph via
  injectable `graph_factory`): auto-resolve, HITL approve/reject over HTTP,
  409/404/422 paths, API-key gate. Full suite 167 passed; ruff + mypy clean on
  the new code.
- **Live smoke test** on this PC: `/health` → submitted a checkout alert →
  root cause at confidence 0.92 → auto-resolved in 11 steps, audit trail served
  from file. (Run in `RUN_MODE=mock` to avoid real Gmail sends.)

**Decisions** — ADR-0019 (FastAPI LAN layer; lead chose Windows/FastAPI/LAN/git-clone
via AskUserQuestion), ADR-0020 (Groq decommissioned `llama-3.3-70b-versatile` —
every LLM call 404'd; lead chose `qwen/qwen3.8-27b`; verified live). PRD_CHANGES C-12.

**Blockers** — none. **Next** — clone on the spare PC, run
`deploy\setup_server.ps1`, then `deploy
un_server.ps1 -OpenFirewall`, and test
from this PC with `deploy\send_test_incident.ps1`.

---

## 2026-07-26 — Phase 4: Evaluation & Documentation → tagged `v1.0.0` (portfolio-ready)

**Done** — all 5 work items (WI-34..WI-38).

- **Fixture world** (`tools/fixtures.py`, ADR-0015): 15 services → symptom-specific
  logs/metrics/deploys, so each incident is distinguishable. Three data tools read
  it by default.
- **WI-34** 20 incidents (`data/incidents/`): 10 auto-resolvable, 5 escalation, 5
  tool-failure (with `inject_failures`), each labeled `category` + `expected_outcome`.
- **WI-35** `evaluation/run_eval.py`: runs all 20 live, forces mock notifications,
  injects per-incident tool failures, paces to respect provider rate limits, and
  uses a simulated reviewer at HITL (approve iff a runbook matched — ADR-0018).
- **WI-36** `evaluation/metrics.py`: the 7 PRD metrics + Markdown table.
- **WI-37** full live run → `evaluation/results.json`.
- **WI-38** professional `README.md`: overview, **Mermaid architecture diagram**,
  novelty table, evaluation table, setup, CLI/demo, tech stack, structure.
- Tests: +9 (`test_evaluation.py`) → **157 total**; ruff + mypy clean.

**Hardening surfaced by the eval** (all genuine improvements):
- ADR-0016: runbook query uses deterministic signals (raw logs + alert), not LLM
  prose → no spurious matches → escalation recall 0.67 → **1.00**.
- ADR-0017: `invoke_structured` retries transient LLM errors (429/overload) with
  backoff → absorbs provider rate-limiting.

**Evaluation result (honest):** all 11 auto-resolve incidents resolved (conf 0.90);
all 5 escalations correct. Metrics: recall/recovery/audit/DLQ/avg-steps all **PASS**.
**Resolution 0.79 & precision 0.67** were depressed by **Groq free-tier token
exhaustion** (from a day of live testing) degrading 3 tool-failure incidents
(INC-016/017/019) to **safe escalation** — the intended fail-safe (can't reason →
escalate, never mis-resolve). A prior budget-available run met **all 7** targets
(resolution 0.93, precision 0.86). Logged as C-11; documented in the README with the
caveat. **Project lead chose to ship v1.0.0 now with the transparent note** rather
than wait for the daily reset.

**Next step**
- Portfolio-ready at `v1.0.0`. Optional Phase 5 stretch (WI-39 trajectory
  summarization, WI-40 self-healing supervisor) remains if desired.
- To reproduce the all-pass table: run `evaluation/run_eval.py` on a higher-limit
  (paid) LLM key.

---

## 2026-07-26 — Phase 3: Supervisor Integration & Production Hardening → tagged `v0.3.0`

**Done** — all 6 work items (WI-28..WI-33). Full pipeline live end-to-end.

- **WI-28 Supervisor** (`agents/supervisor.py`): Approach B (ADR-0012) — one flat
  `StateGraph` reusing every Phase 2 node function, chained diagnosis → root cause →
  remediation with kill-switch-guarded phase transitions; `finalize` node persists
  the audit trail per run; `dead_letter` terminal.
- **WI-29 Kill switch**: `total_steps > MAX_TOTAL_STEPS` → `dead_letter` → DLQ file.
- **WI-30 SQLite checkpointer** (`make_sqlite_checkpointer`): state persisted after
  every node; crash-recovery test proves a *fresh* graph resumes a paused run.
- **WI-31 LangSmith tracing** (`utils/observability.py`): env-driven, auto-activates
  when a key is present; CLI reports status. Documented (per lead choice, C-09).
- **WI-32 Gmail MCP** (`utils/notifier.py`, `utils/gmail_mcp.py`): real escalation
  email via `@gongrzhe/server-gmail-autoauth-mcp` over stdio (langchain-mcp-adapters).
  **Verified live** — real email delivered to the configured inbox; audit shows
  `GmailMCPNotifier` via `gmail-mcp`. Windows `npx`→`cmd /c` fix (ADR-0013).
- **WI-33 E2E**: `main.py <incident.json>` runs the pipeline (HITL `--hitl` resume,
  audit file each run); `tests/test_supervisor.py` = 11 e2e tests.

**Release-criteria evidence (v0.3.0):**
- Live: INC-001/002 → **resolved**, INC-003 → **escalated** (real email sent).
- Kill switch → dead-lettered + DLQ file (tested). Tool-failure injection → no crash.
- SQLite crash-recovery + HITL pause/resume (tested). Audit files in `data/audit_trail/`.
- Quality bar: **148 pytest passing**, `ruff` clean, `mypy` clean (42 files).

**Incidents handled this phase (important events):**
- **Gmail OAuth key hygiene:** a `gcp-oauth.keys.json` sat in the repo root, not
  ignored → added OAuth/credential patterns to `.gitignore` (never tracked). Keys
  never reached git.
- **Test isolation bug (ADR-0014):** with `RUN_MODE=prod` in `.env`, supervisor
  tests without an injected notifier **sent real emails** during a test run. Fixed
  with a global `conftest.py` autouse fixture forcing mock notifications, and made
  the `escalate` audit label truthful.

**Notes**
- `.env` has `RUN_MODE=prod` + `GMAIL_MCP_ENABLED=true` (real email on escalation).
  Set `RUN_MODE=mock` for day-to-day dev to avoid sending on every escalation.
- LangSmith key not yet added → traces inert until then (integration ready).

**Next step**
- ⏸️ **Paused for project-lead review** at the `v0.3.0` checkpoint.
- Phase 4 — Evaluation & Documentation (WI-34..38): 17 more incidents (→20),
  `run_eval.py`, `metrics.py`, and the portfolio README. **This is the `v1.0.0`
  portfolio-ready release.**

---

## 2026-07-25 — Phase 2: Individual Subgraphs → tagged `v0.2.0`

**Done** — all 17 work items (WI-11..WI-27), three subgraphs built and tested.

**LLM provider (ADR-0009 / C-05, lead-directed):** OpenAI key was inactive
(500/connection errors), so switched to **Groq** (`llama-3.3-70b-versatile`) behind
a one-line-switchable abstraction: `LLM_PROVIDER` env flag + `utils/llm.get_llm()`.
Verified Groq structured output live. Nodes never import a provider. Also handled
the key-security incident: keys had been pasted into the tracked `.env.example`;
moved to git-ignored `.env`, restored the template (details in that session's notes
below). LangSmith tracing disabled until Phase 3.

**Subgraphs (all take tools/LLM via dependency injection → unit-testable offline):**
- **Diagnosis** (`agents/diagnosis.py`): `pull_logs`, `pull_metrics`,
  `analyze_diagnosis` (LLM, severity rubric), `handle_diagnosis_failure`;
  conditional routing with graceful degradation (proceed on partial data).
- **Root cause** (`agents/root_cause.py`): `search_runbooks`, `check_deployments`,
  `analyze_root_cause` (LLM, calibrated confidence).
- **Remediation** (`agents/remediation.py`): `evaluate_confidence` (gates on
  confidence AND severity; P0 never auto-resolves), `execute_fix`, `verify_fix`,
  `human_review` (HITL via `interrupt_before` + MemorySaver), `escalate`,
  `close_incident`; three-branch routing.
- **Shared infra:** `utils/tool_runner.run_tool` (the retry/backoff/classify loop,
  auth = not retryable), `agents/_common.apply_tool_outcome`, `MockMetricsAPI`
  (WI-12 / ADR-0011).

**Decisions this phase:** ADR-0009 (Groq provider abstraction), ADR-0010 (store
audit events as dicts — checkpoint/DLQ-safe; changed the locked schema
representation, C-07), ADR-0011 (MockMetricsAPI, C-08). PRD notes C-05/C-06 (Groq /
gpt-5-nano deviate from locked OpenAI-GPT-4o, lead-approved).

**Release-criteria evidence (v0.2.0):**
- Each subgraph compiles & runs independently on seed incidents.
- **Live (Groq) 3-subgraph chain:** INC-001 → P1, conf 0.90, RB-101 → **resolved**;
  INC-002 → RB-102 → **resolved**; INC-003 → P0 → **escalated** (P0 gate overrode a
  spurious runbook match — the intended safety behaviour).
- Tool-failure injection: `test_tool_runner` proves retry-then-fail (timeout, 4
  attempts) and auth = no-retry; subgraph degradation tests prove no crash.
- Audit completeness: per-subgraph tests assert one event per executed node.
- Quality bar: **137 pytest passing**, `ruff` clean, `mypy` clean (36 files).
- HITL: pause-before-`human_review` then approve→resolved / reject→escalated.

**Blockers / notes**
- OpenAI still pending (key inactive). Switch back is `LLM_PROVIDER=openai` once the
  key works; gpt-5-nano rejects custom temperature — the factory already handles it.

**Next step**
- ⏸️ **Paused for project-lead review** at the `v0.2.0` checkpoint.
- Phase 3 — Supervisor Integration (WI-28..33): wire the 3 subgraphs (Approach B),
  kill switch, SQLite checkpointer, LangSmith tracing, Gmail MCP escalation, E2E.

---

## 2026-07-25 — Phase 1: Foundation → tagged `v0.1.0`

**Done** — all 10 work items (WI-01..WI-10):
- `uv sync --extra dev` bootstrapped the env; `uv.lock` committed. Installed
  langgraph 1.2.9, langchain 1.3.14, langchain-openai 1.4.1, pydantic 2.13.4,
  langgraph-checkpoint-sqlite 3.1.0, langsmith 0.10.10 (all ≥ PRD floors; note
  they are 1.x — logged as C-04 in PRD_CHANGES).
- **WI-09** `config.py` — all thresholds/gates/severity rules/paths + failure &
  resolution taxonomies + `ensure_runtime_dirs()`.
- **WI-01** `state/schemas.py` — `IncidentState` TypedDict (42 fields across the 5
  categories: input/output/control/routing/logging), `AuditEvent` &
  `DeadLetterEntry` Pydantic models, `create_initial_state()`. `audit_trail` uses
  an `operator.add` reducer (ADR-0007).
- **WI-06** `utils/failure_classifier.py` — `classify_failure` (declared-type →
  status-code → TimeoutError → message-scan → unknown) + `classify_response`
  (ok/empty/malformed). Decoupled from tools via duck-typing.
- **WI-02..05** four mock tools (`tools/`) with an injectable `FailureMode`
  (`base.py`) and a shared exception hierarchy (`exceptions.py`); runbook KB +
  deployment history seeded to match the incidents.
- **WI-07** `utils/audit_trail.py` (append/format/save) · **WI-08**
  `utils/dead_letter_queue.py` (send/review) — full JSON round-trip.
- **WI-10** three seed incidents: INC-001 (DB pool → RB-101, resolve), INC-002
  (memory leak → RB-102, resolve), INC-003 (P0, no runbook → escalate).
- `main.py` CLI: `--test-tools`, `--test-state`, `--review-dlq` (pass/fail output
  + exit codes).
- `tests/` — 83 unit tests, every unit tested in isolation.

**Release-criteria evidence (v0.1.0):**
- `python main.py --test-tools` → exit 0; 4 tools × 6 modes = 24/24 checks `[OK]`.
- `python main.py --test-state` → exit 0; all 42 fields present, defaults correct.
- `classify_failure`: TimeoutError→timeout, 429→rate_limit, 401→auth, unknown→unknown ✅.
- `classify_response`: ok / empty (not error) / malformed (error) ✅.
- Audit trail append/format/save ✅; DLQ write/read ✅.
- Quality bar: `uv run pytest` 83 passed · `ruff check .` clean · `mypy .` clean (24 files).

**Decisions** (see DECISIONS.md): ADR-0006 (tools return `Any` at the external
boundary), ADR-0007 (audit reducer pattern), ADR-0008 (relaxed lint/type strictness
for tests only). PRD note C-04 (dependency majors ahead of floors).

**Next step**
- ⏸️ **Paused for project-lead review** at the `v0.1.0` checkpoint.
- On approval: begin **Phase 2 — Individual Subgraphs** (WI-11..WI-27), three
  streams buildable in parallel. First LLM node (WI-13) needs `OPENAI_API_KEY` in
  `.env`.

---

## 2026-07-25 — Phase 0: Project Setup

**Done**
- Read and text-extracted the PRD (`Incident_Response_Agent_Documentation.pdf`, 19 pp).
- Confirmed four setup decisions with the project lead via clarifying questions
  (recorded as ADR-0001..0004 in [DECISIONS.md](DECISIONS.md)):
  1. LLM provider → **keep OpenAI GPT-4o** (per PRD lock).
  2. This session scope → **infrastructure + process only**, pause before Phase 1 code.
  3. Env tooling → **uv**.
  4. Version control → **git init now, tag per phase** (Claude commits + tags).
- Installed `uv` 0.11.32 (via pip; wasn't present).
- Created project scaffolding:
  - `pyproject.toml` (deps pinned to PRD §2.3 floors), `.python-version`, `.gitignore`, `.env.example`.
  - Flat package skeleton with placeholder modules + TODO markers:
    `state/ tools/ utils/ agents/ evaluation/ tests/`, `config.py`, `main.py`.
  - `data/{incidents,audit_trail,dlq}/` with `.gitkeep`.
- Built the documentation system under `docs/`:
  `README.md`, `PHASES.md`, `PROGRESS.md`, `CHANGELOG.md`, `DECISIONS.md`, `PRD_CHANGES.md`.
- Authored `CLAUDE.md` and `.claude/skills/` (`phase-complete`, `log-decision`).

**Decisions**
- Flat package layout (not `src/`) to match the PRD's literal path references and
  the release-criteria commands (`python main.py --test-tools`). → ADR-0005.
- Deferred `uv sync` / lockfile generation to the start of Phase 1, to avoid
  resolving heavy LLM deps before any code needs them.

**Blockers / open questions**
- None blocking. `.env` not created (needs real `OPENAI_API_KEY` / LangSmith key
  from the lead before Phase 3; not required to start Phase 1).

- Initialized git (`main`) and made the initial commit `bddfc30`
  (`chore: bootstrap project scaffolding...`). No tag yet — `v0.1.0` is cut when
  Phase 1's release criteria pass. Excluded `.claude/settings.local.json` (local
  per-user permissions) from version control.

**Next step**
- ⏸️ **Paused for project-lead review of the setup**, per the agreed scope (ADR-0002).
- On approval: run `uv sync --extra dev`, then begin Phase 1 — **WI-01 first**
  (the locked `IncidentState` schema), which everything else depends on.
