---
date: 2026-06-05T00:00:00+00:00
researcher: Michał Leśniewski
git_commit: 9749653f19b5c0dcabd656abdae58b0c13625c68
branch: feature/rate-limit-testing
repository: korpotron
topic: "R4 — Rate-limit boundary edge cases: midnight reset and concurrent submissions"
tags: [research, rate-limit, daily-generation, concurrency, testing]
status: complete
last_updated: 2026-06-05
last_updated_by: Michał Leśniewski
---

# Research: R4 — Rate-limit boundary and concurrency tests

**Date**: 2026-06-05
**Researcher**: Michał Leśniewski
**Git Commit**: 9749653f19b5c0dcabd656abdae58b0c13625c68
**Branch**: feature/rate-limit-testing
**Repository**: korpotron

## Research Question

What is the current rate-limit implementation in the daily generation flow, what test coverage already exists, and what specific gaps must Phase 3 testing close for R4 (rate-limit boundary edge cases)?

## Summary

The rate-limit implementation is **correct and race-condition safe**: it uses `select_for_update()` inside a `transaction.atomic()` block to serialize concurrent requests, stores one `DailyGenerationCount` row per (user, date), and relies on `timezone.now().date()` (UTC) for the midnight boundary. Five tests cover the happy path, rejection at limit, `DAILY_GENERATION_LIMIT=0` unlimited mode, LLM error rollback, and next-day reset.

**The single meaningful gap is a concurrency test.** No test verifies that the `select_for_update` lock actually serializes two simultaneous requests — one must succeed and the other must be rejected when both arrive at count=limit-1. The test plan marks Phase 3 coverage as "Partial" precisely because of this missing case.

---

## Detailed Findings

### DailyGenerationCount model

**File:** `core/models.py:54–68`

```python
class DailyGenerationCount(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_generation_counts",
    )
    date = models.DateField()
    count = models.IntegerField(default=0)

    class Meta:
        unique_together = [("user", "date")]
```

- One row per (user, date); the unique constraint enforces this at the DB level.
- No custom manager or queryset methods — all logic is inline in the view.
- Migration created at `core/migrations/0004_dailygenerationcount.py`.

### Generate view — rate-limit logic

**File:** `core/views.py:202–236`

**UTC date anchor (line 202):**
```python
today = timezone.now().date()
```
`settings.TIME_ZONE = "UTC"`, so `.date()` always returns the UTC calendar date. Midnight boundary is implicit: a new UTC day produces a new `date` value.

**Atomic check-and-increment (lines 206–236):**
```python
with transaction.atomic():
    if settings.DAILY_GENERATION_LIMIT > 0:
        limit = settings.DAILY_GENERATION_LIMIT
        existing = (
            DailyGenerationCount.objects.select_for_update()
            .filter(user=request.user, date=today)
            .first()
        )
        current_count = existing.count if existing is not None else 0
        if current_count >= limit:
            return JsonResponse(
                {"error": "You've reached your daily generation limit. ..."},
                status=429,
            )
    # ... LLM call ...
    DailyGenerationCount.objects.update_or_create(
        user=request.user,
        date=today,
        defaults={"count": F("count") + 1},
        create_defaults={"count": 1},
    )
```

Key design properties:
- `select_for_update()` acquires a pessimistic row-level lock on the (user, date) record for the duration of the transaction. A second concurrent request from the same user on the same day blocks until the first transaction commits.
- `DAILY_GENERATION_LIMIT=0` (or any value ≤ 0) skips the entire check block — unlimited mode.
- `F("count") + 1` in `update_or_create` is an atomic DB-side increment (no read-modify-write in Python).
- The increment only commits if the LLM call succeeds; any exception rolls back the transaction.
- HTTP 429 is returned when the limit is reached.

**DAILY_GENERATION_LIMIT setting (korpotron/settings.py:121):**
```python
DAILY_GENERATION_LIMIT = int(os.environ.get("DAILY_GENERATION_LIMIT", "100"))
```
Default is 100. Set to 0 for unlimited.

---

### Existing rate-limit test coverage

**File:** `tests/test_generate.py:264–344`

The `today` fixture (line 267–271) calls `timezone.now().date()` to match the view's own date anchor — tests never mock the clock.

| Test | Lines | Scenario | Assertions |
|------|-------|----------|------------|
| `test_daily_limit_not_reached` | 274–287 | count=1, limit=2 → 200 | HTTP 200; DB count becomes 2 |
| `test_daily_limit_reached` | 290–301 | count=2, limit=2 → 429 | HTTP 429; `"error"` in JSON; LLM not called |
| `test_daily_limit_zero_means_unlimited` | 304–316 | count=999, limit=0 → 200 | HTTP 200 |
| `test_daily_limit_llm_error_does_not_increment` | 319–328 | LLM raises → 502 | HTTP 502; no DB row created |
| `test_daily_limit_resets_next_day` | 331–344 | yesterday's row, limit=1 → 200 | HTTP 200 (yesterday's count ignored) |

All rejection tests assert HTTP status + JSON shape + confirm the LLM is never called — **the generation call itself is blocked**, not just a UI message.

---

## Code References

- `core/models.py:54–68` — `DailyGenerationCount` model definition
- `core/views.py:202–236` — Rate-limit check + atomic increment in generate view
- `korpotron/settings.py:121` — `DAILY_GENERATION_LIMIT` env var wiring
- `core/migrations/0004_dailygenerationcount.py` — Table and unique constraint migration
- `tests/test_generate.py:264–344` — All existing rate-limit tests
- `tests/test_generate.py:267–271` — `today` fixture (no clock mock)

---

## Architecture Insights

**Locking scope:** `select_for_update()` locks only the single (user, date) row. Concurrent requests from *different* users are not serialized against each other — the lock is per-user-per-day, which is correct.

**New-user first-request edge case:** When no `DailyGenerationCount` row exists yet (first generation of the day), `select_for_update().filter(...).first()` returns `None`, and `current_count` defaults to 0. The lock still holds at the transaction level, but since there is no row to lock, two truly simultaneous first-of-day requests could each see `current_count=0` before either inserts. The `unique_together` constraint and `update_or_create` ensure only one row is created, but the second request may succeed before the count is checked again. This is the scenario a concurrency test needs to surface.

**Midnight precision:** The view uses `timezone.now().date()` which changes atomically at UTC midnight. There is no background job or scheduled reset — "reset" is emergent: a new date key naturally produces a new row with count=0.

---

## Gap Analysis for Phase 3

| R4 sub-scenario | Status | Notes |
|---|---|---|
| Generation at daily limit + 1 rejected (HTTP 429) | **Covered** | `test_daily_limit_reached` |
| LLM not called when blocked | **Covered** | `mock_generate.assert_not_called()` in `test_daily_limit_reached` |
| `DAILY_GENERATION_LIMIT=0` = unlimited | **Covered** | `test_daily_limit_zero_means_unlimited` |
| LLM error does not increment counter | **Covered** | `test_daily_limit_llm_error_does_not_increment` |
| UTC midnight boundary reset (yesterday's count ignored) | **Covered** | `test_daily_limit_resets_next_day` |
| Concurrent requests: `select_for_update` serializes, only one can succeed | **NOT COVERED** | No test exists; this is the gap |
| First-of-day request (no existing row, two simultaneous) | **NOT COVERED** | Edge case of the concurrent gap above |

**The single gap the plan must close:** a test that fires two concurrent Django test client requests when count = limit - 1 and verifies exactly one gets HTTP 200 and one gets HTTP 429, confirming the atomic check-and-increment path works end-to-end.

Approaches for a concurrency test in Django:
- `threading.Thread` with a `Barrier` to synchronize launch, then check response codes
- Or: verify the lock behavior indirectly via DB state assertions (both requests complete; count ends at exactly `limit`, not `limit + 1`)
- The test plan guidance calls for "Django integration tests with mocked `timezone.now()`" — mocking the clock is not actually needed for this gap (the real clock is fine); the complexity is in the threading.

---

## Historical Context

- `context/archive/2026-06-04-daily-generation-limit/` — prior change that shipped the `DailyGenerationCount` model, the view logic, and the five existing tests; this Phase 3 work extends that coverage rather than replacing it.
- `context/foundation/test-plan.md §5` marks the rate-limit coverage as "Partial → Phase 3" specifically because of the concurrency case.

---

## Open Questions

1. **Concurrency test technique:** Should the test use `threading.Thread` (real DB concurrency) or a simpler two-phase approach that verifies the DB count ends at exactly `limit` after two sequential requests at the boundary? The simpler approach won't catch TOCTOU bugs if the lock is ever removed, but is deterministic and avoids test flakiness.
2. **Clock mocking scope:** The test plan mentions "mocked `timezone.now()`" — this is needed if we want to test the precise midnight transition (e.g., request at 23:59:59 vs 00:00:01), but the current `test_daily_limit_resets_next_day` already covers the multi-day scenario adequately via separate DB rows. Decide in planning whether clock mocking adds real signal or is redundant.
