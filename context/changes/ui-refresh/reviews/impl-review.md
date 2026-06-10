<!-- IMPL-REVIEW-REPORT -->

# Implementation Review: UI Refresh Implementation Plan

- **Plan**: context/changes/ui-refresh/plan.md
- **Scope**: All 4 phases
- **Date**: 2026-06-10
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical 2 warnings 1 observation

## Evidence

`uv run pytest` → 59 passed · `uv run ruff check .` → clean · `uv run ruff format --check .` → clean ·
`uv run manage.py check` → clean · `uv run manage.py collectstatic --noinput` → OK · `docker build .` → OK (exit 0). All
planned files present in the diff; delete tests correctly updated to assert 204 (plan-review F1 addressed); landing
login modal removed per user request and documented in Progress 2.4 (not a scope breach).

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

### F1 — GET to a delete URL returns HTTP 500

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/views.py:54-63, 129-138
- **Detail**: Both DeleteViews override `form_valid` to return 204 but do not restrict the HTTP method, and Phase 3
  deleted the `*_confirm_delete.html` templates. A GET to `/templates/<pk>/delete/` or `/option-groups/<pk>/delete/`
  falls through to `DeleteView.get()`, which renders the now-missing confirm template → `TemplateDoesNotExist` → 500.
  Confirmed via probe test: `GET /templates/1/delete/` → 500
  (`TemplateDoesNotExist: core/template_confirm_delete.html`). This is exactly plan-review finding F2, which recommended
  the fix below; it was not applied. No UI links to these URLs remain, but a bookmark/crawler/refresh of an old confirm
  URL yields a 500 in production rather than a clean 405.
- **Fix**: Add `http_method_names = ["post"]` to both `TemplateDeleteView` and `OptionGroupDeleteView`. GET then returns
  405 instead of 500. Two-line change, no effect on the JS delete path.
  - Strength: Removes a production-reachable 500; matches the plan-review's pre-identified fix.
  - Tradeoff: None significant.
  - Confidence: HIGH — verified the 500 with a probe test in this repo.
  - Blind spot: None significant.
- **Decision**: FIXED — added `http_method_names = ["post"]` to both TemplateDeleteView and OptionGroupDeleteView

### F2 — "← Edit text" during loading shows a false "timed out" error

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: templates/core/generate.html:258-266, 278-283
- **Detail**: `backToInput()` (bound to the loading-state "← Edit text" button `#loading-cancel`) calls
  `controller.abort()`. The fetch rejects with `AbortError`, and the `catch` runs before the `finally` clears `inFlight`
  — so `inFlight` is still true and `if (inFlight) showError('The request timed out…')` fires. The inline comment claims
  to "distinguish a timeout from a user-initiated cancel", but no flag actually does so: both the 65s timeout and a
  manual cancel produce the same `AbortError` with `inFlight` true. Result: cancelling a generation surfaces a red "The
  request timed out" bar on the input, contradicting the plan's contract that Edit text "restores the input state with
  the prior text intact."
- **Fix**: Add a `cancelled` flag set true in `backToInput()` before `abort()` and reset in `doGenerate()`; gate the
  timeout message on `!cancelled` so a user cancel restores the input cleanly with no error. A few lines, isolated to
  the generate script.
  - Strength: Makes the code match its own comment and the plan contract; removes a confusing error on a normal action.
  - Tradeoff: Minor added state in the closure.
  - Confidence: HIGH — traced the control flow (abort → catch before finally, inFlight still true).
  - Blind spot: None significant.
- **Decision**: FIXED — added `cancelled` flag; `backToInput()` sets it before abort; timeout message gated on
  `!cancelled`

### F3 — Login "next" read from request.GET, lost on failed POST

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: templates/registration/login.html:39
- **Detail**: The hidden `next` field is rendered from `request.GET.next`. On a failed login (POST), there is no GET
  query string, so `next` is dropped and the next successful login goes to `LOGIN_REDIRECT_URL` (home) instead of the
  originally requested protected page. Django's `LoginView` exposes `next` in the template context for exactly this
  case.
- **Fix**: Render `<input type="hidden" name="next" value="{{ next }}">` from the context var, unconditionally, instead
  of gating on `request.GET.next`.
- **Decision**: FIXED — replaced `{% if request.GET.next %}` gate with unconditional `{{ next }}` context var
