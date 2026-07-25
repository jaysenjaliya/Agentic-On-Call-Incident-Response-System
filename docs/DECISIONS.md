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
