# Daily Generation Limit — Plan Brief

> Full plan: `context/changes/daily-generation-limit/plan.md`

## What & Why

Add a per-user daily generation limit controlled by a `DAILY_GENERATION_LIMIT` env var (default 100; `0` = unlimited). The limit exists to keep LLM API costs in check after the app is deployed and accessible to others. When a user hits the limit they see a friendly inline error message; the counter resets at midnight UTC.

## Starting Point

The generation flow (`core/views.py:144`) calls `llm.generate()` with no persistence and no rate limiting. Three models exist (`Template`, `OptionGroup`, `Option`) — no usage tracking model is present.

## Desired End State

A user who has made N successful generations today (N ≥ configured limit) clicks Generate and sees: "You've reached your daily generation limit. Please try again tomorrow." displayed in the existing inline error alert. Setting `DAILY_GENERATION_LIMIT=0` disables the check entirely. A new `DailyGenerationCount` model tracks (user, date, count).

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
|---|---|---|
| Counter storage | New DB model `DailyGenerationCount(user, date, count)` | Consistent with the project's data-model-first approach; survives restarts; roadmap named F-02 as the prerequisite for counter storage. |
| Count timing | After successful LLM call only | Users should not be penalized for LLM errors or connectivity issues. |
| UI enforcement | Error-on-attempt (API-level only) | Avoids a DB query on every page load; consistent with how LLM errors already surface via the inline error alert. |
| HTTP status | 429 Too Many Requests | Semantically correct for rate limiting; distinguishes from 400 (validation) and 502 (LLM failure). |
| Reset boundary | Midnight UTC (`timezone.now().date()`) | `USE_TZ = True` is set; `timezone.now()` is UTC; using `date.today()` would break on non-UTC servers. |

## Scope

**In scope:** New model + migration, `DAILY_GENERATION_LIMIT` setting + env var, limit check in `generate_api`, counter increment after success, tests for 5 enforcement paths.

**Out of scope:** Remaining-count display, pre-disabled Generate button on page load, counting failed LLM attempts, per-template or per-IP limits, admin UI for the counter.

## Architecture / Approach

Minimal surface area: one new model, one env var, two code blocks added to the existing `generate_api` function. The frontend requires no changes — the existing `#error-alert` div already handles JSON error responses from the API.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Data model and settings | `DailyGenerationCount` model + migration + `DAILY_GENERATION_LIMIT` env var | Negligible — pure schema addition with no behaviour change. |
| 2. Enforcement and tests | Limit check + counter increment in `generate_api` + 5 new tests | Low — logic touches only one function; existing tests continue to pass. |

**Prerequisites:** MVP (F-01, F-02, S-03) is complete and on `master`.
**Estimated effort:** ~1 session across 2 phases.

## Open Risks & Assumptions

- The `get_or_create` + `F("count") + 1` pattern is not fully atomic across concurrent requests, but the roadmap explicitly states accuracy is not required.
- `docker build .` is listed as a Phase 2 gate per `lessons.md`; the new model and migration should not affect the build.

## Success Criteria (Summary)

- A user at the daily limit gets a 429 with a friendly error message displayed inline.
- Setting `DAILY_GENERATION_LIMIT=0` allows unlimited generations regardless of counter value.
- LLM errors do not consume the user's daily budget.
