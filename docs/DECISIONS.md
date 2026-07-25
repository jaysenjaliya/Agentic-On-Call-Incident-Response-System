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
