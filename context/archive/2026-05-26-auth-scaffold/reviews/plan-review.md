<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Auth Scaffold Implementation Plan

- **Plan**: context/changes/auth-scaffold/plan.md
- **Mode**: Deep
- **Date**: 2026-05-27
- **Verdict**: REVISE → SOUND (all findings fixed during triage)
- **Findings**: 0 critical | 2 warnings | 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | WARNING |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | WARNING |
| Plan Completeness | WARNING |

## Grounding

6/6 paths ✓ (settings.py, urls.py, pyproject.toml, templates/ absent [expected], tests/ absent [expected], .env.example present) | 3/3 symbols ✓ (AuthenticationMiddleware, context_processors.auth, django.contrib.auth in INSTALLED_APPS) | brief↔plan mostly ✓ (brief's .env prerequisite absent from plan — flagged as F2)

## Findings

### F1 — Logout not covered by automated tests despite "all three behaviours" claim

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: End-State Alignment
- **Location**: Desired End State + Phase 3
- **Detail**: Desired End State says "All three behaviours are covered by automated tests" (redirect, login, logout). But Phase 3 defined three tests for redirect, valid login, and invalid login — logout was never tested automatically.
- **Fix A ⭐ Applied**: Added `test_logout_redirects_to_login` as a 4th test in Phase 3 (POST /accounts/logout/ with authenticated client, assert 302 to /accounts/login/). Updated success criteria and Progress to reflect 4 tests.
- **Decision**: FIXED via Fix A

### F2 — SECRET_KEY prerequisite missing from plan

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: All phases — Phase 1 manual verification, Phase 3 automated
- **Detail**: settings.py:12 reads `SECRET_KEY = os.environ["SECRET_KEY"]` with no default and no dotenv loading. Without `.env` created from `.env.example`, every manage.py command and pytest invocation fails with `KeyError`. The plan-brief.md mentioned this prerequisite but plan.md had no prerequisites section.
- **Fix Applied**: Added a Prerequisites section to plan.md after Current State Analysis.
- **Decision**: FIXED

### F3 — LOGOUT_REDIRECT_URL value unspecified in Phase 1 contract

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1, Changes Required — item 1 (Settings)
- **Detail**: Phase 1 contract listed three constants to add but only showed the value for LOGIN_REDIRECT_URL. Without LOGOUT_REDIRECT_URL set, Django 6 renders the admin's logged_out.html instead of redirecting to the login page (confirmed in .venv source), causing Phase 2 manual step 2.4 to fail.
- **Fix Applied**: Specified all three values in the contract: `LOGIN_URL = "/accounts/login/"`, `LOGIN_REDIRECT_URL = "/"`, `LOGOUT_REDIRECT_URL = "/accounts/login/"`.
- **Decision**: FIXED
