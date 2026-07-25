# Progress Log

Reverse-chronological worklog. Newest entry on top. Each working session gets an
entry: what was done, decisions, blockers, and the next step. Dates are absolute.

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
