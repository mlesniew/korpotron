<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Core Data Model Implementation Plan

- **Plan**: context/changes/core-data-model/plan.md
- **Scope**: Phases 1–2 of 2
- **Date**: 2026-05-28
- **Verdict**: APPROVED
- **Findings**: 0 critical  1 warning  1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Evidence

- `uv run manage.py check` — System check identified no issues (0 silenced).
- `uv run manage.py makemigrations --check` — No changes detected.
- `uv run ruff check .` — All checks passed.
- `uv run pytest` — 10 passed (4 auth + 6 core models).
- `docker build .` — addressed via the `.dockerignore` `!core/` fix committed in 30250d6; Phase 2 checkbox 2.4 marked done.
- Manual admin checks (1.6–1.8) marked done in 4f0f3b6.

All planned files landed and match their contracts: three models (fields, FKs, CASCADE, related_names, `Meta.ordering`, typed `__str__`), `@admin.register` classes with correct `list_display`, `"core"` in `INSTALLED_APPS`, initial migration, consolidated `tests/conftest.py` `user` fixture, local fixture removed from `test_auth.py`, and all 6 model tests. Both plan-review observations (shared fixture; drop `default_auto_field`) were applied.

## Findings

### F1 — Unplanned .dockerignore edit (!core/)

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: .dockerignore:7
- **Detail**: `!core/` was added to the allowlist-style `.dockerignore`. Not in the plan's "Changes Required" list, so technically an EXTRA change. But it is necessary and correct: the `.dockerignore` ignores everything then re-allows specific dirs, so without `!core/` the new app would not be copied into the image and the Phase 2 success criterion `docker build .` would fail. The only gap is that the plan didn't enumerate it. Ties into the lessons.md Docker-build rule.
- **Fix**: None needed — the change is correct and the plan is already closed out. Carry forward as a pattern: every new top-level app dir needs a matching `!<app>/` line in `.dockerignore`. Candidate for /10x-lesson.
- **Decision**: SKIPPED

### F2 — Admin list_display on FK columns triggers per-row queries

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/admin.py:8,13,18
- **Detail**: `list_display` includes FK columns (`"user"`, `"group"`), so the admin changelist issues one extra query per row to render them (classic N+1). Negligible now — admin is dev-only inspection at MVP scale, exactly as the plan scoped it. Noting only so it's on record if these tables grow or the admin gets used heavily.
- **Fix**: Optional, defer — add `list_select_related = ["user"]` / `["group"]` to the respective ModelAdmins if it ever matters.
- **Decision**: FIXED — added list_select_related to all three ModelAdmins in core/admin.py
