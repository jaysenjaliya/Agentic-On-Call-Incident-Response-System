# Architecture Decision Records (ADRs)

Every significant decision is recorded here with its context, the choice made,
the alternatives considered, and the consequences. Newest at the bottom (append
only; supersede rather than delete). Use the `log-decision` skill to add one.

**Status values:** Proposed · Accepted · Superseded by ADR-XXXX · Deprecated

---

## ADR-0001 — LLM provider: keep OpenAI GPT-4o
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Project lead
- **Context:** The PRD locks OpenAI GPT-4o (§2.3, §4.1 — changeable only with
  project-lead approval). Work is happening inside Claude Code, which nudges
  toward Anthropic models. Real fork in the road.
- **Decision:** Target **OpenAI GPT-4o** via `langchain-openai`. Requires
  `OPENAI_API_KEY`.
- **Alternatives:** (a) Switch to Claude/Anthropic — rejected: deviates from a
  locked spec for a portfolio brief. (b) Provider-agnostic factory — rejected
  for now as extra scope; can revisit as a refactor if desired.
- **Consequences:** Faithful to the PRD. LLM calls need an OpenAI key before
  Phase 2 (first LLM node, WI-13).

## ADR-0002 — Session scope: infrastructure + process only
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Project lead
- **Context:** Kickoff session. Option to also start Phase 1 code.
- **Decision:** Do **setup + process only** (repo, docs, CLAUDE.md, skills,
  scaffolding), then **pause for review** before writing Phase 1 product code.
- **Consequences:** Placeholder modules carry TODO markers instead of logic.
  Clean checkpoint for the lead to review the approach before build begins.

## ADR-0003 — Environment & dependency tooling: uv
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Project lead
- **Decision:** Use **uv** for the virtualenv and dependency management;
  `pyproject.toml` + `uv.lock`. uv installed via pip (v0.11.32).
- **Alternatives:** venv+pip+requirements.txt; conda — not chosen.
- **Consequences:** `uv sync` bootstraps the env. Lockfile committed for
  reproducibility. Contributors need uv installed.

## ADR-0004 — Version control: git init now, tag per phase
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Project lead
- **Decision:** Initialize git immediately; Claude Code makes commits and creates
  the semantic-version tags (`v0.1.0` … `v1.0.0`) at each phase boundary, per the
  `phase-complete` skill.
- **Consequences:** Every phase is a recoverable checkpoint (PRD §6 intent).

## ADR-0005 — Flat package layout (not `src/`)
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Claude (default,
  ratified in setup)
- **Context:** The PRD references paths like `state/schemas.py`, `tools/`,
  `config.py`, `main.py` at the top level, and release criteria run
  `python main.py --test-tools`.
- **Decision:** Use a **flat layout** — top-level packages (`state/ tools/ utils/
  agents/ evaluation/`) with `config.py` and `main.py` at the repo root.
- **Alternatives:** `src/` layout — rejected: would break the PRD's literal path
  references and the documented CLI commands for marginal packaging benefit.
- **Consequences:** `pyproject.toml` lists the packages explicitly for the wheel
  build target.

## ADR-0006 — Mock tools return `Any` at the external boundary
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Claude (Phase 1)
- **Context:** Tools must exercise both novelty paths: exceptions (→
  `classify_failure`) and a *malformed but non-exception* payload (→
  `classify_response`). A truncated-JSON string is the realistic malformed case,
  but that conflicts with a precise `list[dict]` return annotation.
- **Decision:** Mock tool fetch/send methods are annotated `-> Any` (an external
  API boundary genuinely can return anything). Normal shape is documented and
  enforced via `*_KEYS` constants + `classify_response(required_keys=...)`.
  MALFORMED mode returns `MALFORMED_PAYLOAD` (a raw string); EMPTY returns an
  empty container.
- **Alternatives:** raise `MalformedResponseError` in MALFORMED mode — rejected:
  then `classify_response`'s malformed branch would have no producer to test.
- **Consequences:** mypy stays green; the ok/empty/malformed classifier is
  exercised end-to-end by `--test-tools` and the tool tests.

## ADR-0007 — Audit trail via `operator.add` reducer; helper returns an event
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Claude (Phase 1)
- **Context:** Nodes must "return only the fields they modify" (PRD §3.2) yet
  every node appends exactly one audit event (FR-8). Mutating a shared list breaks
  state discipline and concurrent-safe merging.
- **Decision:** `IncidentState.audit_trail` is
  `Annotated[list[AuditEvent], operator.add]`. `append_audit_event(...)` *returns*
  an `AuditEvent`; a node appends via `return {"audit_trail": [event]}` and the
  reducer concatenates. This is the LangGraph idiom.
- **Consequences:** Phase 2 nodes follow one uniform append pattern; audit
  completeness is checkable per node.

## ADR-0008 — Relax lint/type strictness for tests only
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Claude (Phase 1)
- **Context:** Test assertions/parametrize rows run long, and pytest
  fixtures/parametrize values fight strict signature typing.
- **Decision:** ruff ignores `E501` under `tests/**`; mypy sets
  `disallow_untyped_defs = false` for `tests.*`. **Product code stays fully
  strict** (100-char lines, typed defs). Test correctness is validated by running
  them.
- **Alternatives:** wrap every long test line / annotate every test fn — rejected
  as noise with no safety benefit.
- **Consequences:** `ruff` and `mypy` are clean repo-wide without diluting the
  product-code bar.

## ADR-0009 — Temporary LLM provider: Groq (behind a provider abstraction)
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Project lead
- **Context:** The OpenAI key was not yet active during Phase 2 (500/connection
  errors on every OpenAI call). The lead directed using Groq in the meantime. The
  PRD locks OpenAI (ADR-0001), so this is an approved temporary deviation.
- **Decision:** Add a one-line-switchable provider abstraction. `LLM_PROVIDER`
  (`.env`) selects `openai` or `groq`; `utils/llm.get_llm()` builds the right
  model. Nodes never import a provider. Temporary model: Groq
  `llama-3.3-70b-versatile` (OpenAI-compatible, supports structured output/tool
  calling). Target remains OpenAI `gpt-5-nano` (also recorded: the lead chose
  gpt-5-nano over the PRD's gpt-4o — see C-06/C-08).
- **Alternatives:** block Phase 2 until OpenAI works (rejected — wasteful);
  hard-swap to Groq with no abstraction (rejected — makes the OpenAI switch-back
  costly). Provider abstraction now pays for itself.
- **Consequences:** Switching back is `LLM_PROVIDER=openai` in `.env`. The factory
  omits `temperature` for OpenAI reasoning models (gpt-5/o-series) that reject it.
  Supersedes the "no abstraction" stance in ADR-0001's alternatives.

## ADR-0010 — Store audit events as dicts in state (not model instances)
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Claude (Phase 2)
- **Context:** With `AuditEvent` model instances in `state["audit_trail"]`, the
  LangGraph checkpointer warned it would soon **block** serializing the unregistered
  type, and the DLQ needed manual conversion. Phase 3 leans hard on the SQLite
  checkpointer.
- **Decision:** `audit_trail` stores plain dicts (`AuditEvent.model_dump()`). The
  `AuditEvent` Pydantic model stays as the constructor/validator in
  `append_audit_event`. The whole `IncidentState` is now JSON-/checkpoint-native.
- **Alternatives:** register the type with the msgpack serde (fragile, per-entry
  config); keep models and set env flags (brittle). Rejected.
- **Consequences:** Locked-schema representation changed (`list[AuditEvent]` →
  `list[dict]`); logged as C-07. Trail readers use dict keys. DLQ `_serialize_state`
  simplified. No checkpoint warnings.

## ADR-0011 — Add MockMetricsAPI as a fifth mock tool
- **Date:** 2026-07-25 · **Status:** Accepted · **Decider:** Claude (Phase 2)
- **Context:** FR-2 requires pulling logs AND metrics; Phase 1 shipped four mock
  tools with no dedicated metrics source.
- **Decision:** Add `MockMetricsAPI` (same `FailureMode` contract) so `pull_metrics`
  has an independent second data source — which is what makes graceful degradation
  (logs-fail/metrics-ok) demonstrable.
- **Alternatives:** fold metrics into `MockLogAPI` (muddies the two data sources);
  read metrics off the alert (not "current metrics" per FR-2). Rejected.
- **Consequences:** Within PRD §4.1 "additional tools" latitude (logged C-08).
  `--test-tools` now exercises five tools.

## ADR-0012 — Supervisor: Approach B (flat graph reusing Phase 2 node functions)
- **Date:** 2026-07-26 · **Status:** Accepted · **Decider:** Claude (per PRD §6.3)
- **Context:** Two ways to wire the supervisor: A = embed the compiled Phase 2
  subgraphs as nodes; B = one flat graph with all nodes + phase routing. PRD §6.3
  recommends starting with B (faster to build/debug).
- **Decision:** Approach B. `agents/supervisor.py` imports the Phase 2 node
  *functions* (not the compiled subgraphs) and wires them into one `StateGraph`
  with kill-switch-guarded phase transitions and a single checkpointer.
- **Alternatives:** Approach A — deferred; nesting subgraph checkpointers/interrupts
  under a parent checkpointer is fiddly. A single flat graph gives one clean
  checkpointer + one `interrupt_before` for HITL.
- **Consequences:** All Phase 2 node logic reused verbatim; one SQLite checkpointer
  covers crash recovery AND HITL resume. Refactor to A remains possible later.

## ADR-0013 — Windows: launch MCP stdio servers via `cmd /c`
- **Date:** 2026-07-26 · **Status:** Accepted · **Decider:** Claude (Phase 3)
- **Context:** `npx` on Windows is `npx.cmd`; asyncio's `subprocess_exec` (used by
  the MCP stdio client) can't launch `.cmd` files directly → `WinError 193`.
- **Decision:** `GmailMCPNotifier` detects `os.name == "nt"` and wraps the command
  as `cmd /c <command> <args>`. POSIX unchanged.
- **Consequences:** Gmail MCP server starts on Windows; verified live (19 tools,
  real send). Env overrides (`GMAIL_MCP_COMMAND/ARGS`) still honoured.

## ADR-0014 — Truthful notifier audit + global test mock-notification guard
- **Date:** 2026-07-26 · **Status:** Accepted · **Decider:** Claude (Phase 3)
- **Context:** The `escalate` node hard-coded `tool_used="MockNotificationService"`,
  so the audit lied when Gmail MCP was active. Worse, supervisor tests that didn't
  inject a notifier picked up `RUN_MODE=prod` from `.env` and **sent real emails**.
- **Decision:** (1) `escalate` records `type(notifier).__name__` and the receipt
  `channel`. (2) `tests/conftest.py` autouse fixture forces `RUN_MODE=mock` +
  `GMAIL_MCP_ENABLED=false` for **every** test — no test can spawn MCP or send email.
- **Consequences:** Audit trail is accurate (`GmailMCPNotifier` via `gmail-mcp`).
  Test suite is hermetic and fast (~2.5s) regardless of developer `.env`.

## ADR-0015 — Shared per-service fixture "world" for the tools
- **Date:** 2026-07-26 · **Status:** Accepted · **Decider:** Claude (Phase 4)
- **Context:** Every service previously returned the *same* DB-pool logs, so a
  20-incident eval would feed identical signals for a memory-leak and a novel
  incident — biasing the LLM and making outcomes meaningless.
- **Decision:** `tools/fixtures.py` maps each service → a symptom → coherent
  logs/metrics/deploys. Auto-resolvable symptoms carry a runbook's keywords (+ a
  suspect deploy); "novel_*" symptoms carry none (→ no match → escalate). The three
  data tools read fixtures by default (override kept for tests).
- **Consequences:** Distinguishable, reproducible incidents. Mock data content is
  flexible per PRD §4.1.

## ADR-0016 — Runbook search uses deterministic signals, not LLM prose
- **Date:** 2026-07-26 · **Status:** Accepted · **Decider:** Claude (Phase 4)
- **Context:** Building the runbook query from the LLM's free-text diagnosis let it
  hallucinate a runbook keyword (e.g. "latency") for a novel incident → spurious
  match → misrouted away from escalation. Observed live: escalation recall 0.67.
- **Decision:** `_build_runbook_query` uses only raw alert fields + raw log
  messages (deterministic), not `diagnosis_summary`/`failing_component`.
- **Consequences:** Novel incidents reliably match no runbook → escalate. Recall
  → 1.00. Root-cause tests unchanged.

## ADR-0017 — Retry transient LLM errors (rate limits) with backoff
- **Date:** 2026-07-26 · **Status:** Accepted · **Decider:** Claude (Phase 4)
- **Context:** A burst of ~40 eval LLM calls tripped Groq rate limits; nodes
  degraded to defaults (severity P3, confidence 0.0) and escalated everything.
- **Decision:** `utils.llm.invoke_structured` wraps the structured LLM call and
  retries **only transient** errors (429/overload/5xx) with linear backoff;
  non-transient errors still raise → node degradation. Eval also paces incidents.
- **Consequences:** The pipeline absorbs provider rate-limiting; eval results are
  stable. Applies to both LLM nodes.

## ADR-0018 — Simulated reviewer at the HITL checkpoint during evaluation
- **Date:** 2026-07-26 · **Status:** Accepted · **Decider:** Claude (Phase 4)
- **Context:** Mid-confidence incidents pause at `human_review`; automated eval
  can't block on a human. Blanket-approving masked genuine escalations.
- **Decision:** In `run_eval`, the simulated reviewer **approves** only when a
  runbook matched (a known remedy exists), otherwise **rejects** → escalate —
  mirroring real reviewer judgment. Recorded per incident (`hitl_decision`).
- **Consequences:** HITL incidents resolve/escalate sensibly; eval never stalls.
  This policy is documented in the README's evaluation notes.

## ADR-0019 — Serve the pipeline over a FastAPI LAN deployment layer
- **Date:** 2026-08-27 · **Status:** Accepted · **Decider:** Project lead
- **Context:** The lead wants the project running on a real live server (a spare
  Windows PC on the LAN) and testable over the network. The PRD scopes a CLI
  only; the architecture (graph, state, tools, routing) is locked at v1.0.0.
- **Decision:** Add an HTTP layer as a pure extension: `server/app.py` (FastAPI)
  wraps the unchanged supervisor graph — POST `/incidents` runs an alert on a
  2-worker thread pool with the SQLite checkpointer, GET `/incidents/{id}` polls
  status, POST `/incidents/{id}/hitl` applies approve/reject to a paused run,
  plus `/audit`, `/dlq`, `/health`. Optional `SERVER_API_KEY` → `X-API-Key`
  gate. Deployment via git clone + `deploy/*.ps1` scripts; LAN-only by design.
  Confirmed with the lead via AskUserQuestion (OS=Windows, layer=FastAPI,
  network=LAN-only, deploy=git clone).
- **Alternatives:** Running the existing CLI over SSH/RDP (no real server,
  rejected by lead); Docker image (extra install/build burden on the spare PC);
  internet exposure via tunnel (unneeded for a few-hours LAN test, larger
  attack surface).
- **Consequences:** The system is demonstrable as a network service; HITL works
  over HTTP and paused runs survive server restarts. New optional dependency
  group `server` (fastapi, uvicorn). No locked component was modified — the
  server calls the same `build_supervisor_graph` / `make_sqlite_checkpointer` /
  `run_config` the CLI uses. Not hardened for the public internet (documented).

## ADR-0020 — Replace decommissioned Groq model with qwen/qwen3.8-27b
- **Date:** 2026-08-27 · **Status:** Accepted · **Decider:** Project lead
- **Context:** During the live-server smoke test every LLM call returned 404:
  Groq decommissioned `llama-3.3-70b-versatile` (ADR-0009's temporary model).
  The pipeline degraded safely (escalated with "root cause undetermined"), but
  a working model is needed. Account's model list offered `openai/gpt-oss-120b`,
  `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`, and others.
- **Decision:** Set `GROQ_MODEL=qwen/qwen3.8-27b` (lead's choice via
  AskUserQuestion; recommendation had been gpt-oss-120b). Updated `.env`,
  the `config.py` default, and `.env.example`. Verified with a live run:
  correct root cause at confidence 0.92, auto-resolved in 11 steps.
- **Alternatives:** `openai/gpt-oss-120b` (larger, recommended; not chosen),
  `openai/gpt-oss-20b` (faster/weaker), switching to `LLM_PROVIDER=openai`
  (target per ADR-0001, but the OpenAI key situation is unchanged).
- **Consequences:** Pipeline works on Groq again; provider remains temporary
  per ADR-0009 (OpenAI stays the locked target). Model behavior (confidence
  calibration, prose style) may differ from the old Llama — evaluation metrics
  in the README were measured on the old model.

## ADR-0021 — Accept per-request tool-failure injection on the live server
- **Date:** 2026-08-28 · **Status:** Accepted · **Decider:** Project lead
- **Context:** The seeded tool-failure incidents (INC-016..020) carry an
  `inject_failures` map that `evaluation/run_eval.py` applies by constructing
  the mock tools with failure modes. The HTTP server built one graph at startup
  with healthy tools, so it silently ignored that field — the five resilience
  incidents ran as ordinary happy-path runs. Since the PRD's stated engineering
  point is surviving tool failures rather than the happy path, the live server
  could not demonstrate the thing the project is about.
- **Decision:** `POST /incidents` accepts an optional validated
  `inject_failures` map (sources `logs`/`metrics`/`runbooks`/`deployments`;
  modes from `FailureMode`). When present the server compiles a per-incident
  graph carrying the failing tool instances, **sharing the one checkpointer** so
  HITL pause/resume and state reads still work; the graph is retained for that
  incident (so a resumed run keeps the same failing tools) and dropped when the
  run terminates. Unknown source/mode → 422. `data_sources_failed` and
  `matched_runbook_id` were added to the status payload as degradation evidence.
- **Alternatives:** Leaving the server happy-path only (rejected — hides the
  project's core behaviour); rebuilding the single shared graph per request
  (wasteful and racy across concurrent incidents); a separate `/chaos` endpoint
  (duplicates the submit path for no gain).
- **Consequences:** The live server demonstrates graceful degradation (NFR-4),
  the confidence→HITL→escalation chain, and the DLQ over HTTP. Verified live:
  `{"metrics":"timeout"}` → resolved on partial data; `{"runbooks":"timeout"}`
  → confidence 0.7 → HITL pause → reject → escalated. No locked component
  changed — injection only swaps the already-injectable tool arguments of
  `build_supervisor_graph`. Mock tools remain the only injectable surface.

## ADR-0022 — Redirect `/` to the API docs instead of adding a dashboard
- **Date:** 2026-08-28 · **Status:** Accepted · **Decider:** Project lead
- **Context:** The bare server URL (`http://<host>:8000/`) returned 404, since
  the API lives under `/health`, `/incidents`, `/docs`. A browser dashboard was
  offered as an alternative.
- **Decision:** `GET /` issues a redirect to `/docs` (the existing Swagger UI).
- **Alternatives:** A custom live dashboard (submit/poll/approve in the browser)
  — richer demo surface but a new UI to build and maintain, declined by the
  lead; leaving the 404 — poor first impression for anyone opening the URL.
- **Consequences:** The root URL is immediately useful and Swagger already
  provides a click-through way to submit incidents and apply HITL decisions,
  so no bespoke UI is carried. If a portfolio demo later needs a friendlier
  surface, the dashboard remains an open option.
