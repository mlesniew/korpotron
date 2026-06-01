<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Auth Scaffold

- **Plan**: context/changes/auth-scaffold/plan.md
- **Scope**: Phases 1–3 of 3 (all complete)
- **Date**: 2026-05-28
- **Verdict**: APPROVED
- **Findings**: 0 critical, 2 warnings, 3 observations

Automated checks re-run during review (all green):

- `uv run manage.py check` → no issues
- `uv run ruff check .` → all checks passed
- `uv run pytest` → 4 passed
- `uv run mypy` (new files) → no issues

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | WARNING |

## Findings

### F1 — Invalid-login test under-asserts vs. plan contract

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: tests/test_auth.py:34-40
- **Detail**: Plan Phase 3 contract says "status 200 (form re-rendered with error)". The test asserts only `status_code == 200`; it never verifies login actually failed. A regression where the form dropped its error, or the template stopped rendering the form, would still pass — the behavioural half of the criterion is untested.
- **Fix**: Add `assert not response.wsgi_request.user.is_authenticated` (and/or `assert response.context["form"].errors`) so the test proves the rejection, not just the 200.
- **Decision**: FIXED — added `assert not response.wsgi_request.user.is_authenticated` and `assert response.context["form"].errors`

### F2 — change.md claims email login (explicitly out of scope)

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: context/changes/auth-scaffold/change.md:10
- **Detail**: change.md summary says "Users can log in with email + password." The implementation uses Django's default User (username field) — login form and tests both use `username`. The plan lists "email-as-username" under "What We're NOT Doing". The identity doc overstates the feature and will mislead the roadmap / future readers.
- **Fix**: Change "email + password" → "username + password" in change.md.
- **Decision**: FIXED — changed "email + password" to "username + password" in change.md

### F3 — Redundant custom `client` fixture shadows pytest-django's

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/test_auth.py:6-8
- **Detail**: pytest-django already ships a `client` fixture (an unauthenticated django.test.Client). The local fixture returns the same thing, adds no behaviour, and invites a future reader to assume it does something special.
- **Fix**: Delete the fixture and rely on pytest-django's built-in `client`.
- **Decision**: FIXED — deleted the redundant `client` fixture; tests now use pytest-django's built-in

### F4 — Plan Prerequisites now stale re: dotenv loading

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: context/changes/auth-scaffold/plan.md:25
- **Detail**: Prerequisites says "no dotenv auto-loading … every command will fail with KeyError if SECRET_KEY is absent." settings.py:9-14 now loads .env conditionally (added post-plan in commit 23a35d1). The plan text no longer matches the code. Minor, and the plan is already closed.
- **Fix**: Optional — leave as-is (plan is closed) or note it's superseded.
- **Decision**: FIXED — annotated stale prerequisite in plan.md as superseded

### F5 — Bootstrap CSS from CDN without Subresource Integrity

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: templates/base.html:7
- **Detail**: The `<link>` to bootstrap.min.css has no `integrity`/`crossorigin` attributes. Real risk is low (CSS-only, no Bootstrap JS loaded, single-user MVP), but a tampered CDN response would load unverified.
- **Fix**: Optional — add the SRI hash + `crossorigin="anonymous"`, or self-host via whitenoise (already configured).
- **Decision**: FIXED — added `integrity` + `crossorigin="anonymous"` to Bootstrap CDN link in base.html
