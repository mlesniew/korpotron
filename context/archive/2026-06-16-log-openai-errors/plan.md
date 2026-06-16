# Log OpenAI Errors Implementation Plan

## Overview

Add server-side logging to the `except OpenAIError` handler in `generate_api` so that LLM/transport failures are visible
in production logs. Currently the handler returns HTTP 502 but records nothing, making outages invisible to operators.

## Current State Analysis

`core/views.py:235-241` catches `OpenAIError` and returns a `JsonResponse(status=502)`. No log call is present. The
module imports no logging machinery.

`core/llm.py` is deliberately silent — its docstring states nothing is logged (non-retention NFR for user content). That
NFR covers user input, prompt text, and model output. It does **not** cover the exception itself, which contains no user
data.

No `LOGGING` dict exists in `korpotron/settings.py`; Django's default propagation to the root logger is in effect.
Gunicorn on Fly.io captures stderr, so ERROR-level entries will appear in production logs without any settings change.

`tests/test_generate.py:217` (`test_generate_llm_error_maps_to_502_not_500`) already exercises the error path but only
asserts the HTTP response — it does not assert that the error was logged.

## Desired End State

When `llm.generate()` raises any `OpenAIError` subclass (timeout, auth failure, rate limit, etc.), a log record at ERROR
level including the full exception traceback is emitted under the logger name `core.views`. The HTTP behaviour (502, no
user input echoed) is unchanged.

### Key Discoveries

- `core/views.py` has no `import logging` — this is the first logging usage in app code.
- `APITimeoutError` is a subclass of `OpenAIError`; both the existing timeout test and the generic error test hit the
  same handler.
- pytest-django provides the `caplog` fixture for asserting log output in tests; no extra dependencies needed.

## What We're NOT Doing

- No `LOGGING` dict in `settings.py` — defaults are sufficient.
- No structured/JSON logging — out of scope; a separate observability task if ever needed.
- No logging in `core/llm.py` — the non-retention NFR covers that layer entirely.
- No changes to the HTTP response shape or status codes.

## Implementation Approach

Three-line change to `core/views.py` (one import, one module-level constant, one call) plus a one-line extension to the
existing test. No new files, no new dependencies.

## Phase 1: Add logger and wire exception call

### Overview

Wire Python's standard `logging` module into `core/views.py` and call `logger.exception()` inside the
`except OpenAIError` block. Extend the existing 502 test to assert the error was actually logged.

### Changes Required

#### 1. Add logging import to `core/views.py`

**File**: `core/views.py`

**Intent**: Import Python's `logging` module and declare a module-level logger so the view can emit log records under
the name `core.views`.

**Contract**: Two lines near the top of the file (with existing stdlib imports): `import logging` and
`logger = logging.getLogger(__name__)`.

#### 2. Call `logger.exception()` in the `except OpenAIError` handler

**File**: `core/views.py`

**Intent**: Emit an ERROR-level log record including the full traceback whenever `llm.generate()` raises. The log
message must not reference the user's input text, template content, or model output.

**Contract**: Inside the `except OpenAIError:` block (before the `return`), add:
`logger.exception("LLM generation failed")`. The bare message string is intentionally content-free; the exception type
and traceback appended automatically provide the diagnostic signal.

#### 3. Assert logging in the existing 502 test

**File**: `tests/test_generate.py`

**Intent**: Extend `test_generate_llm_error_maps_to_502_not_500` to verify that an ERROR-level log record is emitted
when `OpenAIError` is raised — making the logging behaviour part of the tested contract.

**Contract**: Add `caplog` to the test's parameter list; wrap the `_post(...)` call with
`caplog.at_level(logging.ERROR, logger="core.views")`; assert `any(r.levelno == logging.ERROR for r in caplog.records)`
after the response assertions.

### Success Criteria

#### Automated Verification

- Linting passes: `uv run ruff check .`
- Tests pass (including the extended 502 test): `uv run pytest tests/test_generate.py -v`
- Full test suite green: `uv run pytest`

#### Manual Verification

- Trigger a generation failure locally (e.g. set `OPENROUTER_API_KEY=bad`) and confirm an ERROR entry with traceback
  appears on the dev server console.

---

## Testing Strategy

### Unit Tests

- `test_generate_llm_error_maps_to_502_not_500` — extended with `caplog` to assert ERROR record is emitted.
- Existing `test_generate_timeout_maps_to_friendly_error` continues to pass unchanged (it exercises the same handler via
  a different `OpenAIError` subclass).

### Manual Testing Steps

1. Copy `.env`, set `OPENROUTER_API_KEY=invalid`.
2. Run `uv run manage.py runserver` and submit a generation request.
3. Confirm the console shows a line like `ERROR core.views LLM generation failed` followed by a traceback.
4. Restore `.env` and confirm the happy path still works.

## References

- Swallowed error identified in: `core/views.py:235-241`
- Existing test extended: `tests/test_generate.py:217`
- Non-retention NFR documented in: `core/llm.py` module docstring

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Add logger and wire exception call

#### Automated

- [x] 1.1 Linting passes: `uv run ruff check .` — 87744c5
- [x] 1.2 Tests pass (extended 502 test): `uv run pytest tests/test_generate.py -v` — 87744c5
- [x] 1.3 Full test suite green: `uv run pytest` — 87744c5

#### Manual

- [x] 1.4 ERROR entry with traceback visible on console when generation fails — 87744c5
