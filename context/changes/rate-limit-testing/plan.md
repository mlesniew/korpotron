# Phase 3 — LLM & Abuse Surface Tests Implementation Plan

## Overview

Close all three Phase 3 test-plan risks (R4, R5, R6) with targeted additions to two test files. No production code changes; no new models or views. The work is entirely additive test coverage.

## Current State Analysis

The rate-limit implementation (`core/views.py:202–236`) is correct: `select_for_update()` inside `transaction.atomic()` serializes concurrent requests, `F("count") + 1` is an atomic DB-side increment, and the UTC date key resets naturally at midnight.

Five existing tests in `tests/test_generate.py:264–344` cover all sequential rate-limit scenarios (happy path, rejection at limit, unlimited mode, LLM error rollback, next-day reset). One concurrent scenario is missing.

`tests/test_llm.py:34–69` tests that user text IS in the user-message slot but never asserts it is absent from the system-message slot — leaving the structural prompt-injection guard unverified.

`test_generate_creates_no_db_rows` (`tests/test_generate.py:235–261`) verifies row counts don't increase but doesn't scan text fields for the literal input string — the pattern contract for future endpoints is implicit, not enforced.

### Key Discoveries

- `core/views.py:206` — `with transaction.atomic()` wraps the full check-and-increment path; `select_for_update()` at line 209 acquires a pessimistic row-level lock per (user, date)
- `core/models.py:54–68` — `DailyGenerationCount` has a `unique_together = [("user", "date")]` constraint enforced at DB level
- `tests/test_generate.py:267–271` — `today` fixture calls `timezone.now().date()` (no clock mock); the same approach works for concurrency tests
- `tests/test_llm.py:57–69` — `test_build_messages_user_block_delimits_instructions_and_content` asserts user text is IN the user message; it does not assert the system message is clean
- S-07 and S-11 endpoints are not yet implemented (roadmap status: planned); R6 coverage for those must be added alongside each endpoint when it ships

## Desired End State

Three gaps from the Phase 3 test-plan risk map are closed:

- **R4**: Two threading tests confirm `select_for_update()` serializes concurrent boundary requests — one test at an existing-row boundary (`count = limit - 1`) and one at the first-of-day boundary (no pre-existing row). Running `uv run pytest tests/test_generate.py -k "concurrent"` returns two passing tests.
- **R5**: A focused negative-assertion test confirms user-supplied text is absent from `messages[0]["content"]` (the system-message slot). Running `uv run pytest tests/test_llm.py -k "system_message"` returns a passing test.
- **R6**: `test_generate_creates_no_db_rows` scans all text fields of persisted Template, OptionGroup, and Option objects for the literal input string and is annotated as the R6 non-retention pattern contract.

`uv run pytest` passes in full; `uv run ruff check .` returns no errors.

## What We're NOT Doing

- No production code changes (views, models, settings)
- No mocking of `timezone.now()` — the existing `today` fixture's approach (real clock) is sufficient for all new tests
- No R5/R6 tests for S-07/S-11 endpoints (they don't exist yet; those tests go in the PR that ships each endpoint)
- No performance or load tests

## Implementation Approach

Two phases, each adding tests to one or both files. Phase 1 closes R4 with threading tests; Phase 2 closes R5 and R6 with smaller, non-threaded additions. After each phase, run the full test suite and linter.

## Critical Implementation Details

**`transaction=True` is required for the concurrency tests.** Standard `@pytest.mark.django_db` wraps the test in a database transaction (via SAVEPOINT), which makes `select_for_update()` a no-op — both threads see the same row state and the lock never blocks. Only `@pytest.mark.django_db(transaction=True)` commits data between thread-issued queries, enabling the lock to actually serialize requests. A concurrency test using the default marker would appear to pass even if the lock were removed entirely.

---

## Phase 1: Concurrency Tests (R4)

### Overview

Add two threading-based tests to `tests/test_generate.py`. Each test spawns two threads behind a `Barrier`, gives each its own `Client` with `force_login`, applies the `llm.generate` mock before spawning threads, and asserts on the sorted list of response codes plus the final DB count.

### Changes Required

#### 1. Import threading

**File**: `tests/test_generate.py`

**Intent**: Add `import threading` to the module-level imports.

**Contract**: One new import line alongside the existing stdlib imports at line 1–3.

#### 2. Boundary concurrency test

**File**: `tests/test_generate.py`

**Intent**: Prove that when two simultaneous requests arrive with `count = limit - 1`, exactly one succeeds (HTTP 200) and the other is rejected (HTTP 429), and the final DB count equals `limit`.

**Contract**: New test function `test_rate_limit_concurrent_requests_at_boundary`. Markers: `@pytest.mark.django_db(transaction=True)`. Fixtures: `user`, `template`, `settings`, `today`. Sets `DAILY_GENERATION_LIMIT = 2`, creates a `DailyGenerationCount` row at `count=1`. Each thread gets a fresh `Client()`, calls `client.force_login(user)`, waits on the shared `Barrier(2)`, then POSTs to generate. After both threads join, asserts `sorted(statuses) == [200, 429]` and `DailyGenerationCount.objects.get(user=user, date=today).count == 2`.

#### 3. First-of-day concurrency test

**File**: `tests/test_generate.py`

**Intent**: Prove that when two simultaneous requests arrive with no pre-existing `DailyGenerationCount` row (first generation of the day at `limit=1`), exactly one succeeds and the other is rejected. This surfaces the `unique_together` + `update_or_create` path where no row exists to lock.

**Contract**: New test function `test_rate_limit_first_of_day_concurrent_requests`. Same marker and fixture pattern as above. Sets `DAILY_GENERATION_LIMIT = 1`, creates no pre-existing count row. After both threads join, asserts `sorted(statuses) == [200, 429]` and `DailyGenerationCount.objects.get(user=user, date=today).count == 1`.

### Success Criteria

#### Automated Verification

- New concurrency tests pass: `uv run pytest tests/test_generate.py -k "concurrent"`
- Full test suite passes with no regressions: `uv run pytest`
- Linter passes: `uv run ruff check .`

#### Manual Verification

- Confirm both new tests are marked `transaction=True` (not the default `@pytest.mark.django_db`)
- Confirm each thread instantiates its own `Client()` rather than sharing one

**Implementation Note**: After completing this phase and all automated verification passes, update the linked GitHub issue to reflect Phase 1 progress. Then pause here for manual confirmation before proceeding to Phase 2.

---

## Phase 2: LLM & Non-Retention Hardening (R5 + R6)

### Overview

Two small, non-threaded additions: a focused negative-assertion test for the system-message slot (R5), and a field-value scan strengthening the existing non-retention test (R6).

### Changes Required

#### 1. System-message negative assertion test (R5)

**File**: `tests/test_llm.py`

**Intent**: Verify that user-supplied input text is structurally excluded from the system-message slot. If `build_messages()` were modified to embed user text in the system prompt, the existing tests would still pass — this test catches that regression.

**Contract**: New test function `test_build_messages_user_text_absent_from_system_message`. Marker: `@pytest.mark.django_db`. Fixtures: `template`. Calls `llm.build_messages(template, [], "Hello there")` and asserts `"Hello there" not in messages[0]["content"]` (system slot is `messages[0]`).

#### 2. Input non-retention field scan (R6)

**File**: `tests/test_generate.py`

**Intent**: Strengthen `test_generate_creates_no_db_rows` to verify the literal input text `"rewrite me"` does not appear in any text field of any Template, OptionGroup, or Option object after the generate call. The existing count check passes even if the generate view starts storing input text in an existing row's field — this scan closes that gap. A docstring marks the test as the R6 non-retention pattern contract for future endpoints.

**Contract**: Within `test_generate_creates_no_db_rows`, after `assert counts() == before`, add an assertion loop that iterates over all `Template`, `OptionGroup`, and `Option` instances and their `CharField`/`TextField` fields, asserting none contain `"rewrite me"`. Add a docstring: `"""R6 non-retention contract: the generate view must not persist user-supplied input text to any DB field. Extend this pattern to each new endpoint that accepts user text."""`

### Success Criteria

#### Automated Verification

- R5 test passes: `uv run pytest tests/test_llm.py -k "system_message"`
- Full test suite passes: `uv run pytest`
- Linter passes: `uv run ruff check .`

#### Manual Verification

- R5 test name makes the intent self-evident (negative assertion, system slot)
- R6 docstring in `test_generate_creates_no_db_rows` names it as the R6 pattern contract explicitly

**Implementation Note**: After completing this phase and all automated verification passes, update and close the linked GitHub issue. Then pause here for final manual confirmation.

---

## Testing Strategy

### Unit Tests

- R5 is a pure unit test of `build_messages()` — no HTTP request, no DB write beyond fixtures

### Integration Tests

- R4 concurrency tests are integration tests requiring real DB transactions (`transaction=True`)
- R6 runs as part of the existing generate integration test

### Manual Testing Steps

1. Run `uv run pytest -v tests/test_generate.py tests/test_llm.py` and confirm all new tests appear and pass
2. Verify no existing tests have regressed
3. Confirm the two concurrency tests are listed with `transaction=True` in the verbose output (pytest marks these differently)
4. Optionally: temporarily remove `select_for_update()` from `core/views.py` and confirm the concurrency tests fail — this validates the tests actually catch the intended regression
5. Run `docker build .` and confirm the build succeeds before committing

## References

- Research: `context/changes/rate-limit-testing/research.md`
- Test plan Phase 3: `context/foundation/test-plan.md §3`
- Risk map: `context/foundation/test-plan.md §2` (R4, R5, R6)
- Rate-limit view: `core/views.py:202–236`
- Existing rate-limit tests: `tests/test_generate.py:264–344`
- Existing LLM tests: `tests/test_llm.py:34–69`
- Non-retention test: `tests/test_generate.py:235–261`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Concurrency Tests (R4)

#### Automated

- [x] 1.1 New concurrency tests pass: `uv run pytest tests/test_generate.py -k "concurrent"`
- [x] 1.2 Full test suite passes with no regressions: `uv run pytest`
- [x] 1.3 Linter passes: `uv run ruff check .`

#### Manual

- [x] 1.4 Confirm both new tests are marked `transaction=True`
- [x] 1.5 Confirm each thread instantiates its own `Client()`

### Phase 2: LLM & Non-Retention Hardening (R5 + R6)

#### Automated

- [ ] 2.1 R5 test passes: `uv run pytest tests/test_llm.py -k "system_message"`
- [ ] 2.2 Full test suite passes: `uv run pytest`
- [ ] 2.3 Linter passes: `uv run ruff check .`

#### Manual

- [ ] 2.4 R5 test name makes the intent self-evident
- [ ] 2.5 R6 docstring in `test_generate_creates_no_db_rows` names it as the R6 pattern contract
