<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Text Generation Flow

- **Plan**: context/changes/text-generation-flow/plan.md
- **Scope**: All Phases (1–4 of 4)
- **Date**: 2026-06-01
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical  4 warnings  1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | WARNING |
| Pattern Consistency | WARNING |
| Success Criteria | WARNING |

## Findings

### F1 — Per-request OpenAI client construction

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: core/llm.py:63–69
- **Detail**: `_get_client()` constructed a new `OpenAI` instance (and httpx connection pool) on every `generate()` call. Every request would tear down and re-open a TCP + TLS connection to OpenRouter. Fine for occasional MVP use; hurts under any real load.
- **Fix**: Converted `_get_client()` to return a module-level singleton. Tests unaffected — `_get_client` is still the patch target.
- **Decision**: FIXED

### F2 — ruff format failures in committed files

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: core/urls.py, korpotron/settings.py, korpotron/urls.py
- **Detail**: `uv run ruff format --check .` exited non-zero and would have reformatted these three files (all within the feature diff). Success criteria 1.4 and 2.4 both required this check to pass.
- **Fix**: Ran `uv run ruff format` on the three files.
- **Decision**: FIXED

### F3 — GenerateView route split across project/app URL files

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architecture
- **Location**: korpotron/urls.py:24 and core/urls.py:16
- **Detail**: `GenerateView` (GET page) was registered in `korpotron/urls.py` while `generate_api` (POST endpoint) lived in `core/urls.py`. All other resource views live entirely in one URL file.
- **Fix (Fix A)**: Moved `GenerateView` from `korpotron/urls.py` into `core/urls.py` as the first route (`path("", GenerateView.as_view(), name="home")`). All 46 tests pass after the move.
- **Decision**: FIXED via Fix A

### F4 — except OpenAIError misses pre-SDK transport exceptions

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/views.py:198–204
- **Detail**: `except OpenAIError` does not cover raw httpx transport exceptions (e.g. DNS failure on misconfigured `OPENROUTER_BASE_URL`) that occur before the SDK wraps them. Those would 500 instead of the friendly 502.
- **Decision**: SKIPPED — 500 on misconfigured transport is acceptable as a server error.

### F5 — Wrong return type annotation in test helper

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/test_generate.py:51
- **Detail**: The `_post` helper was annotated `-> "httpx.Response"` with a `# type: ignore[name-defined]`. Django's test client returns `django.http.HttpResponse`, not `httpx.Response`.
- **Fix**: Changed to `-> HttpResponse` (imported from `django.http`) and removed the `# type: ignore`.
- **Decision**: FIXED
