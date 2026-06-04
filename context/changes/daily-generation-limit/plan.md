# Daily Generation Limit Implementation Plan

## Overview

Add a per-user daily generation limit enforced by the `DAILY_GENERATION_LIMIT` env var (default 100; `0` = unlimited). When a user exceeds their limit, `generate_api` returns a 429 with a friendly error message that the existing inline error alert in `generate.html` displays. Counter resets at midnight UTC.

## Current State Analysis

- `generate_api` (`core/views.py:144`) validates inputs, calls `llm.generate()`, and returns JSON — no persistence of any kind.
- Three models in `core/models.py`: `Template`, `OptionGroup`, `Option`. No usage/counter model exists.
- Settings env vars read via `os.environ.get()` in `korpotron/settings.py` (lines 115–119 pattern to follow).
- Generation page (`templates/core/generate.html`) already handles JSON error responses from `generate_api` via an inline `#error-alert` Bootstrap div — no new UI work needed.
- `USE_TZ = True` (settings.py:100), so `timezone.now().date()` is the correct UTC-date source.

## Desired End State

A logged-in user who has triggered N successful generations today where N ≥ `DAILY_GENERATION_LIMIT` (and limit > 0) receives a 429 response with `{"error": "..."}` from `generate_api`. The existing frontend error alert displays the message. The counter increments only on successful LLM calls. Setting `DAILY_GENERATION_LIMIT=0` disables the check entirely.

### Key Discoveries

- `core/views.py:198`: `llm.generate()` is called here; the limit check belongs just before this line, after all input validation, so malformed requests are rejected cheaply.
- `core/views.py:200`: `OpenAIError` handling returns 502 — counter must NOT increment in this path (after-success-only requirement).
- `tests/test_generate.py:223`: `test_generate_creates_no_db_rows` checks only Template/OptionGroup/Option/Session counts — it will still pass once we add a counter row because `DailyGenerationCount` is not in its tuple.
- Django `F("count") + 1` in `save(update_fields=["count"])` translates to an atomic `UPDATE SET count = count + 1` at the DB level — preferable to `obj.count += 1` which is non-atomic.

## What We're NOT Doing

- No remaining count or reset-time display in the UI (roadmap explicitly excluded this).
- No pre-disabling of the Generate button on page load (error-on-attempt only).
- No counting of failed LLM calls against the daily budget.
- No per-template or per-IP limits — per-user only.
- No admin UI for the counter model.

## Implementation Approach

Two phases: Phase 1 adds the data model and settings plumbing. Phase 2 wires the enforcement logic into `generate_api` and adds tests. Each phase is independently verifiable.

## Critical Implementation Details

**UTC date**: Use `timezone.now().date()` (from `django.utils`) not `date.today()`. With `USE_TZ = True`, `timezone.now()` is UTC; `date.today()` reflects the server's local time zone, which breaks the midnight-UTC-reset invariant on non-UTC servers.

**Atomic counter increment**: Use `get_or_create(..., defaults={"count": 1})` + `F("count") + 1` in a subsequent `save(update_fields=["count"])` for the update case. This translates the increment to a SQL `UPDATE SET count = count + 1`, avoiding the non-atomic read-modify-write of `obj.count += 1`. For the first call (`created=True`), `defaults={"count": 1}` acts as the increment — do not use `0`. The roadmap explicitly says accuracy is not required, but this pattern costs nothing extra.

---

## Phase 1: Data model and settings

### Overview

Add `DailyGenerationCount` model, migration, `DAILY_GENERATION_LIMIT` setting, and `.env.example` documentation. No behaviour change yet — just the foundation.

### Changes Required

#### 1. New `DailyGenerationCount` model

**File**: `core/models.py`

**Intent**: Track how many successful generations a user has triggered on a given UTC date.

**Contract**: New model with fields `user` (FK to `AUTH_USER_MODEL`, CASCADE), `date` (DateField), `count` (IntegerField, default=0). Unique constraint on `("user", "date")`.

#### 2. Migration

**File**: `core/migrations/` (generated)

**Intent**: Apply the new model to the database.

**Contract**: Run `uv run manage.py makemigrations core` then commit the generated file.

#### 3. `DAILY_GENERATION_LIMIT` setting

**File**: `korpotron/settings.py`

**Intent**: Read the limit from the environment so it can be overridden per deployment without a code change.

**Contract**: Add `DAILY_GENERATION_LIMIT = int(os.environ.get("DAILY_GENERATION_LIMIT", "100"))` after the existing `OPENROUTER_*` block. The `int()` cast fails loudly on a malformed value, which is desirable.

#### 4. `.env.example` documentation

**File**: `.env.example`

**Intent**: Tell developers the env var exists and what it does.

**Contract**: Add a commented entry `# DAILY_GENERATION_LIMIT=100  # set to 0 for unlimited` in the optional-vars section (after the existing `OPENROUTER_*` commented entries).

### Success Criteria

#### Automated Verification

- Migration applies cleanly: `uv run manage.py migrate`
- All existing tests still pass: `uv run pytest`
- Lint passes: `uv run ruff check .`

#### Manual Verification

- `uv run manage.py shell -c "from core.models import DailyGenerationCount; print(DailyGenerationCount._meta.get_fields())"` lists the three expected fields.

**Implementation Note**: After completing this phase and all automated verification passes, pause for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Enforcement in `generate_api` and tests

### Overview

Wire the limit check and counter increment into `generate_api`, then add tests covering the key enforcement paths.

### Changes Required

#### 1. Limit check and counter increment in `generate_api`

**File**: `core/views.py`

**Intent**: Reject requests over the daily limit with a 429, and increment the counter after every successful LLM call.

**Contract**:

Add two blocks to `generate_api` — both conditioned on `settings.DAILY_GENERATION_LIMIT > 0`:

*Before the `llm.generate()` call (after group invariant check, line ~196):*
- Compute `limit = settings.DAILY_GENERATION_LIMIT` and `today = timezone.now().date()`.
- Query `DailyGenerationCount` for `(request.user, today)`; treat a missing row as count 0.
- If `count >= limit`, return `JsonResponse({"error": "You've reached your daily generation limit. Please try again tomorrow."}, status=429)`.

*After the successful `llm.generate()` call (before the final `return JsonResponse`):*
- `get_or_create` the counter row for `(request.user, today)` with `defaults={"count": 1}`.
- If the row already existed (`created == False`), set `obj.count = F("count") + 1` and `obj.save(update_fields=["count"])`.

Required new imports: `from django.db.models import F`, `from django.utils import timezone`, `from .models import DailyGenerationCount`.

#### 2. New tests

**File**: `tests/test_generate.py`

**Intent**: Verify the five enforcement cases relevant to correctness.

**Contract**: Five new test functions using `@pytest.mark.django_db`, `settings` fixture (pytest-django) to override `DAILY_GENERATION_LIMIT`, and `unittest.mock.patch("core.views.llm.generate", ...)` as a context manager (matching the existing test pattern — no additional dependency):

- `test_daily_limit_not_reached` — set limit to 2, pre-seed count=1, successful generate → 200 and counter is now 2.
- `test_daily_limit_reached` — set limit to 2, pre-seed count=2, attempt generate → 429, `llm.generate` not called.
- `test_daily_limit_zero_means_unlimited` — set limit to 0, pre-seed count=999, attempt generate → 200.
- `test_daily_limit_llm_error_does_not_increment` — set limit to 5, mock `llm.generate` to raise `OpenAIError`, attempt → 502, counter row absent (or count unchanged).
- `test_daily_limit_resets_next_day` — set limit to 1, pre-seed count=1 for yesterday's date, attempt generate → 200 (today has no counter row yet).

For pre-seeding, create `DailyGenerationCount` rows directly (e.g., `DailyGenerationCount.objects.create(user=user, date=today, count=N)`).

### Success Criteria

#### Automated Verification

- All tests pass: `uv run pytest`
- New tests specifically pass: `uv run pytest tests/test_generate.py -k "daily_limit"`
- Lint passes: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Docker build succeeds: `docker build .`

#### Manual Verification

- With `DAILY_GENERATION_LIMIT=1` in `.env`, generate once → succeeds; generate again → inline error alert shows the limit-reached message.
- With `DAILY_GENERATION_LIMIT=0` in `.env`, generate repeatedly without hitting any limit.

**Implementation Note**: After completing this phase and all automated verification passes, pause for manual confirmation before considering the change complete. Create or update the GitHub issue for `daily-generation-limit`.

---

## Testing Strategy

### Unit Tests

- Limit-reached path returns 429 (not 400 or 500).
- `limit=0` bypasses the check entirely (no DB query for counter).
- LLM error path does not touch the counter.

### Integration Tests

- End-to-end: counter increments correctly across multiple successful calls.
- Date boundary: yesterday's count does not affect today's check.

### Manual Testing Steps

1. Set `DAILY_GENERATION_LIMIT=1` in `.env`, start the dev server.
2. Log in and generate once — result should appear normally.
3. Generate again — the inline error alert should show the limit-reached message.
4. Set `DAILY_GENERATION_LIMIT=0` and reload; generation should work without limit.
5. Verify no regressions on template management, option group management, and login flows.

## Migration Notes

Phase 1 adds one new migration. The table starts empty. No existing data migration needed.

## References

- Roadmap slice S-05: `context/foundation/roadmap.md` (line 38)
- Generation view: `core/views.py:144`
- Existing OpenRouter settings pattern: `korpotron/settings.py:115`
- Existing generation tests: `tests/test_generate.py`

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Data model and settings

#### Automated

- [ ] 1.1 Migration applies cleanly: `uv run manage.py migrate`
- [ ] 1.2 All existing tests still pass: `uv run pytest`
- [ ] 1.3 Lint passes: `uv run ruff check .`

#### Manual

- [ ] 1.4 DailyGenerationCount fields visible via Django shell

### Phase 2: Enforcement in `generate_api` and tests

#### Automated

- [ ] 2.1 All tests pass: `uv run pytest`
- [ ] 2.2 New tests pass: `uv run pytest tests/test_generate.py -k "daily_limit"`
- [ ] 2.3 Lint passes: `uv run ruff check .`
- [ ] 2.4 Format check: `uv run ruff format --check .`
- [ ] 2.5 Docker build succeeds: `docker build .`

#### Manual

- [ ] 2.6 DAILY_GENERATION_LIMIT=1: second generate shows limit-reached message
- [ ] 2.7 DAILY_GENERATION_LIMIT=0: generation works without limit
