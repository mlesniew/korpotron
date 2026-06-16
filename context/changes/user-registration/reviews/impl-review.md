<!-- IMPL-REVIEW-REPORT -->

# Implementation Review: User Registration

- **Plan**: context/changes/user-registration/plan.md
- **Scope**: All 3 phases (full plan)
- **Date**: 2026-06-16
- **Verdict**: NEEDS ATTENTION (low-stakes — all findings are optional polish; nothing blocks shipping)
- **Findings**: 0 critical, 3 warnings, 1 observation

## Verdicts

| Dimension           | Verdict |
| ------------------- | ------- |
| Plan Adherence      | PASS    |
| Scope Discipline    | WARNING |
| Safety & Quality    | WARNING |
| Architecture        | PASS    |
| Pattern Consistency | WARNING |
| Success Criteria    | PASS    |

Automated checks at review time: `ruff check` clean, `ruff format --check` clean, `pytest tests/test_registration.py` 5
passed, full `pytest` 75 passed. Docker build (criterion 3.5) trusted as recorded at e95bec7 (no dependency changes).

## Findings

### F1 — Passphrase compared with non-constant-time `!=`

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/forms.py:66
- **Detail**: `clean_passphrase` does `if value != settings.REGISTRATION_PASSPHRASE`. `!=` short-circuits on the first
  differing byte, so it is timing-variable. Practical risk is low for a shared passphrase (network jitter dominates, no
  per-character oracle), but Django already ships `constant_time_compare` and using it signals intent /
  defense-in-depth.
- **Fix**: Use `from django.utils.crypto import constant_time_compare` and
  `if not constant_time_compare(value, settings.REGISTRATION_PASSPHRASE):`.
- **Decision**: FIXED — swapped `!=` for `constant_time_compare` in core/forms.py

### F2 — Unplanned context processor, CSS classes, and extra hero link

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: core/context_processors.py, static/css/korpotron.css:1174, templates/core/landing.html:6-9,39-42
- **Detail**: Three additions beyond the plan: (a) a new `registration` context processor exposing
  `registration_enabled`, wired correctly in settings.py:69 and used to gate the Register links so they only appear when
  registration is enabled — a genuine improvement over the plan's always-visible link to a 403 route; (b) real CSS
  classes (`.k-login-success`, `.k-login-field-error`, `.k-login-form-footer`) instead of the plan's suggested inline
  styles — cleaner; (c) an extra "No account yet? Register →" hero link plus a `.k-landing-register-link` style block in
  landing.html, pure cosmetic creep. All benign and coherent, but none are documented in the plan.
- **Fix**: Add a short addendum to plan.md noting the context-processor gating, the CSS-class decision, and the hero
  link, so the plan stays the source of truth.
- **Decision**: FIXED — addendum appended to context/changes/user-registration/plan.md

### F3 — Test `settings` fixture annotated `object`, not repo convention

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/test_registration.py:8,17,33,40,57
- **Detail**: New tests annotate the pytest-django `settings` fixture as `settings: object`, while the repo's
  conftest.py:6 uses `settings: pytest.FixtureRequest` for the same fixture. Neither is the truly-correct type, but the
  new file diverges from the established in-repo convention. Markers/fixtures otherwise match.
- **Fix**: Change `settings: object` → `settings: pytest.FixtureRequest` to match conftest.py.
- **Decision**: FIXED — replaced all occurrences in tests/test_registration.py

### F4 — `/register/` has no rate limiting (passphrase is the only barrier)

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — informational
- **Dimension**: Safety & Quality
- **Location**: core/views.py:36-51
- **Detail**: Accounts are created `is_active=True` with no throttling on the endpoint, so a leaked passphrase permits
  unbounded automated signups. This is explicitly the documented S-11 design ("What We're NOT Doing": no rate limiting;
  daily generation limit is the cost guard). Flagging only so the tradeoff is conscious — the whole posture rests on
  passphrase secrecy. No action needed.
- **Decision**: SKIPPED — acknowledged as intentional S-11 design tradeoff
