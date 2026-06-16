# Log OpenAI Errors — Plan Brief

> Full plan: `context/changes/log-openai-errors/plan.md`

## What & Why

The `except OpenAIError` handler in `generate_api` (core/views.py) returns HTTP 502 but emits no log record, making LLM
outages invisible in production. This adds a single `logger.exception()` call so failures appear in server logs with a
full traceback — without touching user content.

## Starting Point

No logging machinery exists in application code today. Django's default log propagation is active and sufficient;
gunicorn on Fly.io already captures stderr at ERROR level.

## Desired End State

Any `OpenAIError` raised by `llm.generate()` produces an ERROR-level log record under `core.views` with a full
traceback. The HTTP contract (502, no user input echoed) is unchanged. The logging behaviour is covered by the test
suite via pytest's `caplog` fixture.

## Key Decisions Made

| Decision                 | Choice                                 | Why (1 sentence)                                                                         |
| ------------------------ | -------------------------------------- | ---------------------------------------------------------------------------------------- |
| Log level                | `logger.exception()`                   | Traceback is needed to distinguish timeout vs auth vs rate-limit failures                |
| Metadata in log message  | None — exception only                  | Keeps the message content-free; the exception itself provides the signal                 |
| Test coverage            | Extend existing 502 test with `caplog` | Prevents a future refactor from re-swallowing the error                                  |
| `LOGGING` in settings.py | No change — rely on defaults           | Django's defaults are sufficient for Fly.io/gunicorn; structured logging is out of scope |

## Scope

**In scope:** `import logging` + module-level logger in `core/views.py`; `logger.exception()` in `except OpenAIError`;
`caplog` assertion in `tests/test_generate.py`.

**Out of scope:** Logging in `core/llm.py` (non-retention NFR applies there); structured/JSON log format; `LOGGING`
settings dict.

## Architecture / Approach

Python stdlib `logging` wired at the view layer only. The logger name `core.views` follows Django convention
(`__name__`). No new dependencies. Three lines of production code, one line added to an existing test.

## Phases at a Glance

| Phase                                 | What it delivers                                        | Key risk                         |
| ------------------------------------- | ------------------------------------------------------- | -------------------------------- |
| 1. Add logger and wire exception call | ERROR log on every `OpenAIError`; caplog test assertion | None — change is trivially small |

**Prerequisites:** None  
**Estimated effort:** ~10 minutes

## Open Risks & Assumptions

- Django's default logging propagation is assumed to reach gunicorn stderr on Fly.io — verified by convention, not
  tested in prod yet.

## Success Criteria (Summary)

- `uv run pytest` passes including the extended 502 test
- ERROR entry with traceback visible on console when a generation request fails with a bad API key
