---
change_id: log-openai-errors
title: Log OpenAI errors server-side for production visibility
status: archived
created: 2026-06-16
updated: 2026-06-16
archived_at: 2026-06-16T17:24:13Z
---

## Notes

In `core/views.py`, the `except OpenAIError` handler in `generate_api` catches LLM/transport failures and returns a 502
to the client, but never logs anything server-side. This means LLM outages or misconfiguration are invisible in
production logs.

The non-retention NFR (no logging of user input, prompt, or model output) does not apply to the error itself — the
exception type, message, and status code from OpenRouter contain no user data and are safe to log. A
`logger.exception()` call inside the handler would give operators visibility without violating the NFR.
