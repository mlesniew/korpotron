# Phase 3 — LLM & Abuse Surface Tests — Plan Brief

> Full plan: `context/changes/rate-limit-testing/plan.md`
> Research: `context/changes/rate-limit-testing/research.md`

## What & Why

Close all three Phase 3 test-plan risks (R4, R5, R6) with targeted additions to two test files. The rate-limit implementation is correct, but its concurrent-request guarantee is unverified by tests; the LLM message slot structure is only half-checked; and the non-retention contract is implicit. These gaps leave the abuse surface unconfirmed.

## Starting Point

Five sequential rate-limit tests exist in `tests/test_generate.py:264–344`; seven LLM tests exist in `tests/test_llm.py:34–69`. No threading-based test exercises the `select_for_update()` lock. No test asserts user text is absent from the system-message slot. The non-retention test counts rows but doesn't scan field values.

## Desired End State

Two new threading tests confirm that concurrent boundary requests are serialized (exactly one 200, one 429). A new LLM test confirms the system-message slot is clean of user text. The non-retention test scans field values and carries a docstring marking it as the R6 pattern contract. `uv run pytest` passes in full.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Concurrency technique | `threading.Thread` + `Barrier` | Actually tests the race condition; sequential assertions wouldn't catch a lock removal | Plan |
| `transaction=True` marker | Required | `select_for_update()` is a no-op inside a test savepoint — only real transactions enable locking | Research + Plan |
| First-of-day edge case | Separate test | Distinct `unique_together` + `update_or_create` path deserves an explicit label in the test suite | Plan |
| Clock mocking | Not used | Real clock is sufficient; `test_daily_limit_resets_next_day` already covers multi-day scenario | Research |
| R6 approach | Strengthen existing test | S-07/S-11 don't exist yet; scan field values and add docstring as pattern contract | Plan |
| Scope | Full Phase 3 (R4+R5+R6) | Close the whole phase in one change rather than leaving R5/R6 as open stubs | Plan |

## Scope

**In scope:**
- 2 threading concurrency tests in `tests/test_generate.py` (R4)
- 1 negative-assertion test in `tests/test_llm.py` (R5)
- Field-value scan + docstring in `test_generate_creates_no_db_rows` (R6)

**Out of scope:**
- Production code changes (views, models, settings)
- Clock mocking / midnight-transition tests
- R5/R6 tests for S-07/S-11 endpoints (ship alongside each endpoint)
- Performance or load tests

## Architecture / Approach

All changes are additive test additions. Phase 1 targets `tests/test_generate.py` with threading-based integration tests using `@pytest.mark.django_db(transaction=True)`. Phase 2 targets both files with small, non-threaded assertions. No new fixtures, no new helper modules — existing patterns are extended in place.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Concurrency Tests (R4) | Two threading tests prove `select_for_update()` serializes concurrent boundary requests | Thread timing; `transaction=True` marker easy to forget |
| 2. LLM & Non-Retention Hardening (R5 + R6) | Negative system-slot assertion + field-value scan with R6 docstring | Small but the R6 scan scope (which models/fields) needs to be explicit |

**Prerequisites:** None — no pending migrations, no production changes required  
**Estimated effort:** ~1 session across 2 phases

## Open Risks & Assumptions

- Threading tests have minor flakiness risk on very slow CI if the barrier doesn't synchronize launch tightly — acceptable given the lock is fast
- R6 field scan covers Template, OptionGroup, Option only; if new models are added that accept user text from generate, they must be added to the scan

## Success Criteria (Summary)

- `uv run pytest tests/test_generate.py -k "concurrent"` returns 2 passing tests
- `uv run pytest tests/test_llm.py -k "system_message"` returns 1 passing test
- `uv run pytest` full suite passes with no regressions
