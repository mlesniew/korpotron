<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Landing Page

- **Plan**: context/changes/landing-page/plan.md
- **Scope**: All Phases (1–3 of 3)
- **Date**: 2026-06-04
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 2 warnings, 3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Findings

### F1 — Hardcoded /accounts/login/ in landing.html

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: templates/core/landing.html:15
- **Detail**: The CTA button uses a hardcoded path `href="/accounts/login/"`. Every other template in the project uses `{% url '...' %}` for internal links. A hardcoded path silently breaks if the auth URLs are ever remounted at a different prefix.
- **Fix**: Replace `href="/accounts/login/"` with `href="{% url 'login' %}"`.
- **Decision**: FIXED — 1253da7

### F2 — LOGOUT_REDIRECT_URL changed outside plan scope

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: korpotron/settings.py:95
- **Detail**: commit 986d944 changed LOGOUT_REDIRECT_URL from "/accounts/login/" to "/". The plan's "What We're NOT Doing" section explicitly stated: "No changes to auth settings (LOGIN_URL, LOGIN_REDIRECT_URL, LOGOUT_REDIRECT_URL)." The change is functionally correct but was made without a plan amendment.
- **Fix A ⭐ Recommended**: Document as a plan addendum and keep the change.
  - Strength: The change is correct behaviour once a public landing page exists. Updating the plan keeps the source of truth accurate.
  - Tradeoff: Plan diverges slightly from what was reviewed/approved.
  - Confidence: HIGH — the change is well-tested and clearly deliberate.
  - Blind spot: None significant.
- **Fix B**: Revert and track as a follow-up.
  - Strength: Restores strict scope discipline.
  - Tradeoff: Reverts correct behaviour; requires a second PR for something already done.
  - Confidence: LOW — reverting is the wrong direction given the feature goal.
  - Blind spot: None.
- **Decision**: FIXED via Fix A — aa89b60

### F3 — Bootstrap CDN hash duplicated between base.html and landing.html

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: templates/core/landing.html:7
- **Detail**: The plan explicitly called for a standalone template (no base.html inheritance) as a deliberate design choice. A natural consequence is that the Bootstrap 5.3.3 CDN link and integrity hash appear in both base.html and landing.html. If Bootstrap is ever bumped, both files need updating.
- **Fix**: No action required now. A comment near the CDN link in landing.html pointing to base.html would help. If Bootstrap is upgraded, update both files.
- **Decision**: FIXED — b5d638e

### F4 — test_unauthenticated_sees_landing_page duplicates coverage

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/test_auth.py:7
- **Detail**: tests/test_auth.py::test_unauthenticated_sees_landing_page and tests/test_generate.py::test_anonymous_home_shows_landing_page both GET / without logging in and assert b"Get started" in content. The generate.py version is strictly stronger (also asserts the generate button is absent). Creates a maintenance coupling on the string "Get started".
- **Fix**: Remove test_unauthenticated_sees_landing_page from test_auth.py and rely on test_generate.py for anonymous-home coverage. Or keep it as a high-level auth smoke test — both are acceptable.
- **Decision**: FIXED — fd0f2bd

### F5 — option_groups queried even when the user has no templates

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/views.py:133–140
- **Detail**: HomeView always fetches both templates and option_groups in the authenticated branch regardless of whether the user has any templates. When the user has none, the generate button is hidden but option groups are still returned. Mirrors the pre-existing behaviour of GenerateView — not a regression.
- **Fix**: Guard the option_groups query behind `if templates:`, or accept as is (two small queries is not a real bottleneck at this scale).
- **Decision**: SKIPPED
