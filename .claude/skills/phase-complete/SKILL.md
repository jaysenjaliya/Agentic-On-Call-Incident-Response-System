---
name: phase-complete
description: Run at the end of every project phase to close it out correctly — verify the PRD release criteria, update all tracking docs, commit, and cut the semantic-version git tag. Use when a phase's work is finished, when the user says a phase is done, or before starting the next phase. Phases and their tags: Phase 1 v0.1.0, Phase 2 v0.2.0, Phase 3 v0.3.0, Phase 4 v1.0.0, Phase 5 v1.1.0.
---

# Phase Completion Checklist

The authoritative procedure for closing a phase. A phase is a Git checkpoint
(PRD §6): if the project stops, the latest tag is the deliverable. Do this
carefully and in order. **Never tag a phase whose release criteria aren't met.**

## 0. Confirm the phase and its tag
Identify which phase is closing and its target version from `docs/PHASES.md`:

| Phase | Tag | Phase | Tag |
|-------|-----|-------|-----|
| 1 Foundation | `v0.1.0` | 4 Evaluation | `v1.0.0` |
| 2 Subgraphs | `v0.2.0` | 5 Stretch | `v1.1.0` |
| 3 Integration | `v0.3.0` | | |

## 1. Verify EVERY release criterion — with evidence
Open `docs/PHASES.md` and go through that phase's release-criteria checklist. For
each one, actually run the command / test and observe the result. Paste or
summarize the evidence in `docs/PROGRESS.md`.
- ✅ criterion passes → check it off in PHASES.md.
- ⛔ criterion fails → **stop.** Fix it, or if it genuinely must be deferred, get
  explicit project-lead approval, mark it ⏭️ with a reason, and log it in
  `docs/PRD_CHANGES.md`. Do not proceed to tagging on unmet P0 criteria.

Also confirm the quality bar (CLAUDE.md §5): `uv run pytest`, `uv run ruff check .`,
and `uv run mypy .` all pass; every node has a docstring and appends exactly one
audit event.

## 2. Bump the version
Set `version` in `pyproject.toml` to the phase's target version.

## 3. Update the tracking docs (all of them)
- **`docs/PHASES.md`** — mark the phase ✅ in the summary table; set "Current
  phase" to the next one; ensure all work-item + criteria boxes reflect reality.
- **`docs/CHANGELOG.md`** — move the phase's items from `[Unreleased]` into a new
  `## [vX.Y.Z] — <today> — Phase N: <name>` section (use the template at the
  bottom of the file). Fill Added/Changed/Fixed.
- **`docs/PROGRESS.md`** — add a dated session entry: what shipped, the criteria
  evidence, decisions, and the next step.
- **`docs/DECISIONS.md`** — ensure any decisions made this phase are ADRs (use the
  `log-decision` skill).
- **`docs/phases/`** — optional per-phase deep-dive note if the phase warrants it.
- Update the root `README.md` if this phase changed user-facing usage (mandatory
  for Phase 4).

## 4. Commit
Stage the phase's work + doc updates. Use a Conventional Commit summarizing the
phase, e.g.:

```
git add -A
git commit -m "$(cat <<'EOF'
feat: complete Phase 1 (Foundation) — state schema, mock tools, utilities

Delivers WI-01..WI-10. All v0.1.0 release criteria verified (see docs/PHASES.md).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
Prefer several smaller commits during the phase and one summarizing commit at the
boundary. Keep the log clean and meaningful (a v1.0.0 release criterion).

## 5. Tag the release
```
git tag -a vX.Y.Z -m "Phase N — <name>: <one-line milestone>"
```
Annotated tags (`-a`) only. Confirm with `git tag --list` and `git log --oneline -5`.

> Pushing to a remote is separate — only push (`git push --follow-tags`) if a
> remote is configured and the project lead has asked for it.

## 6. Announce the checkpoint to the human
Report: the tag created, the criteria that passed (with evidence), anything
deferred and why, and the plan for the next phase. Then **pause for the lead to
review** before starting the next phase, unless they've said to continue.
