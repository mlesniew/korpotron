<!-- IMPL-REVIEW-REPORT -->

# Implementation Review: Phase 3 — LLM & Abuse Surface Tests

- **Plan**: context/changes/rate-limit-testing/plan.md
- **Scope**: Phase 1 + Phase 2 of 2
- **Date**: 2026-06-05
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical 1 warning 1 observation

## Verdicts

| Dimension           | Verdict |
| ------------------- | ------- |
| Plan Adherence      | PASS    |
| Scope Discipline    | WARNING |
| Safety & Quality    | PASS    |
| Architecture        | PASS    |
| Pattern Consistency | WARNING |
| Success Criteria    | PASS    |

## Findings

### F1 — Unplanned settings.py and .gitignore changes

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Scope Discipline
- **Location**: korpotron/settings.py:84–93
- **Detail**: The plan explicitly listed "No production code changes (views, models, settings)". Django 6.x dropped
  select_for_update() support for SQLite in DEFERRED mode, so transaction_mode = IMMEDIATE was added to settings.py. The
  setting applies globally (dev server too). .gitignore updated for the resulting test.sqlite3 file.
- **Fix A ⭐ Recommended**: Document the necessity in the plan as a discovered addendum.
  - Strength: Change is correct and well-commented; documenting syncs plan with reality.
  - Tradeoff: Plan scope guardrail is visibly bent (with explanation).
  - Confidence: HIGH — SQLite/IMMEDIATE is a real Django 6.x constraint.
  - Blind spot: Haven't verified whether any dev workflow relies on deferred SQLite behaviour.
- **Fix B**: Move IMMEDIATE mode to a test-only conftest.py override.
  - Strength: Keeps settings.py clean; matches "no production changes" intent strictly.
  - Tradeoff: More moving parts; conftest DB overrides can interact with transaction=True tests.
  - Confidence: MEDIUM.
  - Blind spot: pytest-django settings overrides can be subtle with transaction=True tests.
- **Decision**: FIXED via Fix A — plan addendum added to plan.md.

### F2 — Inline import added inside test function body

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/test_generate.py:271
- **Detail**: `from django.db import models as _models` added inside function body, deviating from module-level import
  convention.
- **Fix**: Move to module-level imports at top of file.
- **Decision**: FIXED — both `from django.contrib.sessions.models import Session` and
  `from django.db import models as _models` moved to module level.
