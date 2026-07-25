# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres to
[Semantic Versioning](https://semver.org/) with a tagged release at each phase
(PRD §6).

## [Unreleased]

_Nothing yet — Phase 2 (Individual Subgraphs) begins after v0.1.0 review._

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
