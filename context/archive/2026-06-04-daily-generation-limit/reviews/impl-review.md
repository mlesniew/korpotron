<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Daily Generation Limit

- **Plan**: context/changes/daily-generation-limit/plan.md
- **Scope**: Phase 1 + 2 of 2
- **Date**: 2026-06-04
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical  1 warning  3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Findings

### F1 — Test TODAY constant uses date.today() instead of UTC date

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: tests/test_generate.py:255
- **Detail**: The plan's "Critical Implementation Details" explicitly required `timezone.now().date()` (UTC) over `date.today()` (local time). The production view correctly uses `timezone.now().date()`. But the test file defines a module-level constant `TODAY: date = date.today()`. On a non-UTC developer machine (e.g., UTC+2, 23:30 local → UTC 21:30), `date.today()` returns tomorrow relative to UTC. Pre-seeded counter rows land on the wrong date from the view's perspective, so `test_daily_limit_reached` returns 200 instead of 429 and `test_daily_limit_not_reached` fails to find the seeded count. CI on UTC passes; local dev on UTC+2 breaks.
- **Fix**: Replace the module-level constant with a pytest fixture:
  ```python
  @pytest.fixture
  def today() -> date:
      from django.utils import timezone
      return timezone.now().date()
  ```
  Thread `today` as a parameter into each of the five `daily_limit` test functions.
  - Strength: Matches production code exactly; eliminates both timezone skew and midnight-staleness edge case.
  - Tradeoff: Five test signatures gain one parameter.
  - Confidence: HIGH — timezone mismatch is deterministic on non-UTC machines.
  - Blind spot: None significant.
- **Decision**: FIXED — afb0ed8 (replaced module-level TODAY with today fixture using timezone.now().date())

### F2 — today computed twice in generate_api

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/views.py:202, 224
- **Detail**: `timezone.now().date()` is called once in the check block and again in the increment block. A request straddling UTC midnight will check against day D but increment day D+1, creating a new row for D+1 with count=1 instead of updating D's row. Extremely unlikely but trivially avoidable.
- **Fix**: Hoist `today = timezone.now().date()` above the first `if settings.DAILY_GENERATION_LIMIT > 0:` block and remove the second assignment.
- **Decision**: FIXED — 1605471

### F3 — DailyGenerationCount missing __str__

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: core/models.py:54-64
- **Detail**: `Template`, `OptionGroup`, and `Option` all define `__str__`. `DailyGenerationCount` does not.
- **Fix**: Add `def __str__(self) -> str: return f"{self.user} / {self.date} ({self.count})"`
- **Decision**: FIXED — 7570567

### F4 — test_generate_creates_no_db_rows silently ignores counter rows

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/test_generate.py (test_generate_creates_no_db_rows)
- **Detail**: The test asserts no extra DB rows are created by a successful generation, but its `counts()` tuple only covers Template/OptionGroup/Option/Session. With `DAILY_GENERATION_LIMIT=100` (default), a successful generation now inserts a `DailyGenerationCount` row that the test doesn't notice. The test name is now misleading.
- **Fix**: Either add `DailyGenerationCount.objects.count()` to the `counts()` tuple, or set `settings.DAILY_GENERATION_LIMIT = 0` in the test scope to restore the "no rows" intent.
- **Decision**: FIXED — 3f8a91d (Fix A: added DailyGenerationCount to counts() tuple + set limit=0 in test scope)
