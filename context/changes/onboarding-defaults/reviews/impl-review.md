<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Onboarding Defaults

- **Plan**: context/changes/onboarding-defaults/plan.md
- **Scope**: All 4 Phases
- **Date**: 2026-06-05
- **Verdict**: APPROVED (after triage fixes)
- **Findings**: 1 critical  3 warnings  4 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | FAIL → PASS (F2 fixed) |
| Scope Discipline | WARNING → PASS (F2 fixed) |
| Safety & Quality | WARNING → PASS (F4 fixed, F3 accepted, F6 fixed) |
| Architecture | PASS |
| Pattern Consistency | PASS (F8 fixed) |
| Success Criteria | FAIL → PASS (F1 fixed) |

## Findings

### F1 — Two tests failing: OptionGroup count stale after fixture expansion

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: tests/test_onboarding.py:17, 27
- **Detail**: Commit 87f165e expanded the fixture to 6 option groups after tests were written asserting count == 3. Both test_first_login_seeds_defaults and test_second_login_does_not_reseed failed with `assert 6 == 3`.
- **Fix**: Changed both OptionGroup count assertions from `== 3` to `> 0`.
- **Decision**: FIXED (user chose relaxed `> 0` assertion)

### F2 — Fixture expanded to 6 option groups without updating plan or tests

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Adherence / Scope Discipline
- **Location**: core/fixtures/onboarding_defaults.json
- **Detail**: The plan specified exactly 3 option groups. Shipped fixture has 6 groups.
- **Fix A ⭐**: Added addendum to plan's Phase 2 spec documenting the expanded fixture content.
- **Decision**: FIXED via Fix A

### F3 — Unhandled exception on fixture read crashes the login flow

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: core/apps.py:33
- **Detail**: `fixture_path.read_text()` and `json.loads()` are called with no error handling inside the signal handler. A missing or malformed fixture raises uncaught exceptions that break login.
- **Fix**: Accept risk — fixture is version-controlled and always present in the repo.
- **Decision**: ACCEPTED

### F4 — TOCTOU race: concurrent logins can collide on OnboardingState insert

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: core/apps.py:23–35
- **Detail**: Guard checks happened outside `transaction.atomic()`. Concurrent logins could both pass, then collide on the unique OnboardingState insert.
- **Fix B**: Moved all guard checks inside `transaction.atomic()` and added `select_for_update()` on the user row to serialise concurrent seeds.
- **Decision**: FIXED via Fix B

### F5 — Typo in fixture: "caareful phrasing"

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Content quality
- **Location**: core/fixtures/onboarding_defaults.json:58
- **Detail**: Double-a typo in Passive-Aggressive option instruction.
- **Fix**: Corrected to "careful phrasing".
- **Decision**: FIXED

### F6 — Users with pre-existing content never get an OnboardingState row

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/apps.py:26–30
- **Detail**: The content-exists early return skipped writing OnboardingState, causing two extra EXISTS queries on every future login for those users.
- **Fix**: Added `OnboardingState.objects.create(user=user)` on the content-exists path before returning. Updated test assertion from `is False` to `is True` and updated plan spec.
- **Decision**: FIXED + plan and test updated

### F7 — Fixture read/parse on every eligible login

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/apps.py:32–33
- **Detail**: JSON parsed from disk on each first-time login; could be cached at module level.
- **Decision**: SKIPPED

### F8 — Redundant f-string in OnboardingState.__str__

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: core/models.py:79
- **Detail**: `return f"{self.user}"` is equivalent to `return str(self.user)`.
- **Fix**: Changed to `return str(self.user)`.
- **Decision**: FIXED
