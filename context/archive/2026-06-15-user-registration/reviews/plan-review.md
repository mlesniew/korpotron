<!-- PLAN-REVIEW-REPORT -->

# Plan Review: User Registration Implementation Plan

- **Plan**: `context/changes/user-registration/plan.md`
- **Mode**: Deep
- **Date**: 2026-06-15
- **Verdict**: REVISE
- **Findings**: 0 critical, 1 warning, 2 observations

## Verdicts

| Dimension             | Verdict |
| --------------------- | ------- |
| End-State Alignment   | PASS    |
| Lean Execution        | PASS    |
| Architectural Fitness | PASS    |
| Blind Spots           | WARNING |
| Plan Completeness     | WARNING |

## Grounding

7/7 paths ✓, 4/4 symbols ✓, brief↔plan ✓

## Findings

### F1 — Email field renders and validates but is silently dropped

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 1 — Registration form
- **Detail**: `UserCreationForm.Meta.fields = ("username",)` (from `BaseUserCreationForm` at
  `django/contrib/auth/forms.py:224–227`). `UserRegistrationForm` declares `email = EmailField(required=False)` on the
  class but defines no `Meta` override. `ModelForm.save()` only writes fields listed in `Meta.fields`, so `user.email`
  is never set — the value the user typed is silently discarded. The form accepts input it cannot persist.
- **Fix A ⭐ Recommended**: Add a `Meta` subclass to include `email` in fields:
  `class Meta(UserCreationForm.Meta): fields = (*UserCreationForm.Meta.fields, "email")`. Django's ModelForm then writes
  email to `User.email` automatically on `save()` — no `save()` override needed. Strength: one-liner, idiomatic
  ModelForm pattern; no risk of breaking the password save path (password1/password2 are virtual, handled by
  `BaseUserCreationForm.save()` directly). Tradeoff: none significant. Confidence: HIGH — verified against Django source
  at forms.py:246–251. Blind spot: None.
- **Fix B**: Drop the email field entirely — remove `email = EmailField(...)` from the form. Strength: zero risk of data
  confusion; zero code to maintain; consistent with "informational only" brief decision. Tradeoff: diverges from roadmap
  S-11 spec ("username, email, password"). Confidence: HIGH. Blind spot: None.
- **Decision**: FIXED via Fix B — email field dropped from form entirely; plan/brief updated to reflect username-only
  registration

### F2 — Test count says "Four functions" but five are specified

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 3 — Test suite contract
- **Detail**: The contract opens with "Four `@pytest.mark.django_db` test functions" but enumerates five named tests
  (the unset-passphrase case is split into GET and POST variants). The brief's scope section also says "Test suite (4
  scenarios)". An implementer may write four tests and miss one.
- **Fix**: Change "Four" to "Five" in `plan.md` Phase 3 contract and "4 scenarios" to "5 scenarios" in `plan-brief.md`
  scope section.
- **Decision**: FIXED — counts updated in both files

### F3 — Phase 1 Progress section missing the type-checking criterion

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 Success Criteria / `## Progress`
- **Detail**: Phase 1's Automated Verification lists "Type checking passes (mypy, if wired): no new errors on
  `core/forms.py` and `core/views.py`" but there is no matching `- [ ] 1.x` checkbox in the Progress section. The plan's
  own convention requires every Success Criteria bullet to map to a Progress item. The `(mypy, if wired)` qualifier
  makes it conditional, but the asymmetry between sections will confuse `/10x-implement`.
- **Fix**: Either add `- [ ] 1.2 Type checking passes (mypy, if wired)` to Progress §Phase 1 Automated (renumbering
  1.2→1.3, 1.3→1.4), or remove the criterion from Phase 1 Automated Verification entirely since mypy isn't CI-wired yet
  (CLAUDE.md: "mypy — to be wired into CI").
- **Decision**: FIXED — mypy criterion removed from Phase 1 Automated Verification (not CI-wired yet)
