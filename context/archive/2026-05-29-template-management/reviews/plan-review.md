<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Template Management Implementation Plan

- **Plan**: context/changes/template-management/plan.md
- **Mode**: Deep
- **Date**: 2026-05-29
- **Verdict**: REVISE → SOUND (after fixes)
- **Findings**: 0 critical  2 warnings  1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | PASS |
| Plan Completeness | WARNING |

## Grounding

6/6 paths ✓ (`core/models.py`, `korpotron/urls.py`, `korpotron/views.py`, `templates/base.html`, `tests/conftest.py`, `tests/test_auth.py`), 5/5 symbols ✓ (Template model fields, `include` import, `{% if user.is_authenticated %}` block, `user` fixture, APP_DIRS + INSTALLED_APPS), brief↔plan ✓

## Findings

### F1 — Nav bar contract is self-contradictory

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 2, Change 1 — templates/base.html contract
- **Detail**: Contract read "visible only to authenticated users (inside the existing `{% if user.is_authenticated %}` block or alongside it)." The "or alongside it" option places the link outside the auth guard, contradicting the preceding requirement.
- **Fix**: Remove "or alongside it" from the parenthetical.
- **Decision**: FIXED — removed "or alongside it" from Phase 2 base.html contract

### F2 — Phase 1 progress section missing mypy success criterion

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 Success Criteria / Progress section
- **Detail**: Phase 1 Automated Verification listed two bullets (lint + mypy "(if wired)") but Progress only had item 1.1 for lint. The mechanical contract requires every success-criteria bullet to have a matching progress item.
- **Fix**: Add `- [ ] 1.2 Type checking passes: uv run mypy . (if wired)` and renumber manual steps 1.2→1.3, 1.3→1.4, 1.4→1.5.
- **Decision**: FIXED — added 1.2 mypy item and renumbered manual steps

### F3 — Template discovery rationale in brief is imprecise

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: plan-brief.md — Open Risks & Assumptions
- **Detail**: Brief cited "APP_DIRS: True" as the discovery mechanism for `templates/core/` files. Settings has `DIRS: [BASE_DIR / "templates"]`, so those files are found via DIRS, not APP_DIRS. Templates are found correctly — wrong mechanism cited.
- **Fix**: Correct the brief's assumption to cite DIRS as the discovery mechanism.
- **Decision**: FIXED — corrected plan-brief.md assumption
