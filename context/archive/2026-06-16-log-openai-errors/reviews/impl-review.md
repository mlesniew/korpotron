<!-- IMPL-REVIEW-REPORT -->

# Implementation Review: Log OpenAI Errors

- **Plan**: context/changes/log-openai-errors/plan.md
- **Scope**: Phase 1 of 1
- **Date**: 2026-06-16
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical · 1 warning · 2 observations

## Verdicts

| Dimension           | Verdict |
| ------------------- | ------- |
| Plan Adherence      | PASS    |
| Scope Discipline    | PASS    |
| Safety & Quality    | WARNING |
| Architecture        | PASS    |
| Pattern Consistency | PASS    |
| Success Criteria    | PASS    |

## Findings

### F1 — Provider error body may leak user input into logs

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: core/views.py:267
- **Detail**: `logger.exception()` automatically appends the full traceback including `str(exception)`. For transport
  subclasses (`APITimeoutError`, `APIConnectionError`) the message is safe. But for `APIStatusError` subclasses
  (`RateLimitError`, `AuthenticationError`, etc.), the OpenAI SDK constructs the message as
  `Error code: {status_code} - {body}`, where `body` is the raw JSON from the upstream provider. Some providers echo
  contextual details in error bodies — in unusual cases a provider could include a prompt fragment. If that happens,
  user text lands in the server log, violating the non-retention NFR. The plan's assertion "the exception itself
  contains no user data" (plan.md:14) is true for transport errors and the test mock, but is not structurally guaranteed
  for all subclasses in production.
- **Fix A ⭐ Recommended**: Switch to a safe structured log call —
  `logger.error("LLM generation failed: %s (status=%s)", type(e).__name__, getattr(e, 'status_code', None))`
  - Strength: Structurally safe regardless of provider behavior; still emits the actionable signal (error class + status
    code).
  - Tradeoff: Loses the full traceback in logs.
  - Confidence: HIGH — error class + status code is the actionable signal for 99% of LLM outage alerts.
  - Blind spot: None significant.
- **Fix B**: Keep `logger.exception()` and accept the risk — document that provider error bodies may appear in logs.
  - Strength: Preserves full traceback; no code change needed.
  - Tradeoff: Non-retention NFR conditionally violated depending on provider behavior.
  - Confidence: MED — relies on provider behavior, not code.
  - Blind spot: Actual OpenRouter error body formats not audited for all error types.
- **Decision**: FIXED via Fix B — kept logger.exception(); added comment documenting accepted risk of provider body in
  logs.

### F2 — Test doesn't assert log records are clean of user data

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: tests/test_generate.py:229
- **Detail**: The existing `assert "secret input" not in json.dumps(body)` checks the HTTP response. The new log
  assertion checks an ERROR record was emitted. But no assertion checks "secret input" is absent from the log records
  themselves. The non-retention guarantee is half-tested.
- **Fix**: Add `assert all("secret input" not in r.getMessage() for r in caplog.records)` after the existing log
  assertion.
- **Decision**: FIXED — added assert all("secret input" not in r.getMessage() for r in caplog.records) after existing
  log assertion.

### F3 — generate_api docstring now contradicts the logging behavior

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: core/views.py:191–195
- **Detail**: The `generate_api` docstring says the view "Never persists or logs the input/output (hard non-retention
  NFR)." Now that `logger.exception()` has been added to the same function, this statement is literally false. The NFR
  comment removed from the `except` block (correctly) left behind a now-misleading docstring.
- **Fix**: Update the docstring to distinguish: "never persists or logs user input or model output (non-retention NFR);
  infrastructure failures are logged at ERROR level for observability."
- **Decision**: FIXED — updated docstring to distinguish user data non-retention from infrastructure failure logging.
