# Landing Page Implementation Plan

## Overview

Add a public-facing landing page for unauthenticated visitors. The root URL (`/`) becomes auth-aware: anonymous users see a branded hero page with a "Get started" CTA leading to login; authenticated users continue to see the generate UI exactly as today. No URL changes, no data model changes, no migrations.

## Current State Analysis

- `/` routes to `GenerateView` (LoginRequiredMixin + TemplateView) — unauthenticated users get 302 to `/accounts/login/`
- `base.html` uses Bootstrap 5.3.3, dark navbar, `.container mt-4`; all existing app templates extend it
- `LOGIN_REDIRECT_URL = "/"`, `LOGIN_URL = "/accounts/login/"` — both stay unchanged
- Two existing tests assert anonymous `GET /` → 302; both will break and need updating

## Desired End State

Unauthenticated visitors hitting `/` see a full-viewport dark hero page with the Korpotron name, a short tagline, and a "Get started" button that leads to `/accounts/login/`. Authenticated users bypass the landing page entirely and land on the generate UI as before. Auth redirect settings are unchanged.

### Key Discoveries

- `GenerateView` at `core/views.py` uses `LoginRequiredMixin + TemplateView` and passes `templates` and `option_groups` context — the new combined view must replicate this context for the authenticated path
- `test_auth.py:7-10` (`test_unauthenticated_redirects_to_login`) and `test_generate.py:62-65` (`test_generate_page_requires_login`) both assert 302 for anonymous `/`; both need updating
- All other generate tests hit `/` with an authenticated client — they remain valid unchanged

## What We're NOT Doing

- No URL changes — `GenerateView` content stays at `/` (name `"home"`) for authenticated users
- No changes to auth settings (`LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`)
- No registration/signup flow — "Get started" leads to login only
- No mobile-first design — desktop browser use case only per PRD non-goals
- No additional marketing content, screenshots, or feature lists beyond what the hero provides

## Implementation Approach

Replace `GenerateView` with a new `HomeView` that checks `request.user.is_authenticated`. No `LoginRequiredMixin` — the view handles both auth states directly. The anonymous branch renders a standalone `core/landing.html` (no base.html, own Bootstrap CDN link, full-viewport dark hero). The authenticated branch replicates the context and template of the old `GenerateView` (the two querysets: `templates` and `option_groups`).

## Phase 1: View and Routing Change

### Overview

Swap the root URL handler from `GenerateView` to a new `HomeView` that dispatches on auth state.

### Changes Required

#### 1. Replace GenerateView with HomeView

**File:** `core/views.py`

**Intent:** Remove `GenerateView` (which used `LoginRequiredMixin`) and replace it with `HomeView`. The anonymous branch renders `core/landing.html` with no context. The authenticated branch queries `Template` and `OptionGroup` objects filtered by `request.user` (same as `GenerateView` did) and renders `core/generate.html`. The URL name `"home"` is preserved so all existing `{% url 'home' %}` references in templates continue to work.

**Contract:** `HomeView` is a plain `View` subclass (no mixins). `get()` method: if `not request.user.is_authenticated` → `render(request, "core/landing.html")`; else → fetch `templates` and `option_groups` from the DB (same queryset as before) and `render(request, "core/generate.html", {...})`.

#### 2. Update URL registration

**File:** `core/urls.py`

**Intent:** Replace `GenerateView.as_view()` with `HomeView.as_view()` at `path("", ..., name="home")`. Remove the `GenerateView` import; add `HomeView` import.

### Success Criteria

#### Automated Verification

- `uv run pytest tests/test_generate.py tests/test_auth.py` passes (after Phase 3 test updates) *(verifiable after Phase 2 — landing.html must exist first)*
- `uv run ruff check .` passes
- `uv run ruff format .` produces no diff

#### Manual Verification

- Anonymous `GET /` → landing page (200, hero content visible, no app nav links) *(verifiable after Phase 2 — landing.html must exist first)*
- Authenticated `GET /` → generate UI (200, same as before the change)
- No regression: `test_generate_page_lists_only_own`, `test_generate_page_renders_form_and_options`, and `test_generate_page_empty_state_when_no_templates` still pass

**Implementation Note:** After completing this phase, pause here for manual confirmation of criteria 1.5 and 1.6 only (authenticated path and regression tests are immediately verifiable). Criteria 1.1 and 1.4 require Phase 2's `landing.html` template and will be verified after Phase 2.

---

## Phase 2: Landing Page Template

### Overview

Create the standalone `core/landing.html` template — a full-viewport dark hero with no base.html inheritance, own Bootstrap CDN link, no navbar.

### Changes Required

#### 1. Create landing.html

**File:** `templates/core/landing.html`

**Intent:** A self-contained HTML page (does not extend `base.html`) with a full-viewport dark background. Center-aligned hero content: `<h1>Korpotron</h1>`, a `<p class="lead">` tagline, and an `<a>` styled as a Bootstrap primary button linking to `/accounts/login/`. Include the Bootstrap 5.3.3 CDN link (same URL as `base.html`). No navbar — the hero CTA is the sole entry point.

**Contract:** Page structure — `<html lang="en">` with `<meta viewport>`, Bootstrap 5.3.3 CDN `<link>`, `<body class="bg-dark text-white">`, a single `<div>` using flexbox to fill 100vh and center content vertically and horizontally. Placeholder copy:

- Headline: `Korpotron`
- Tagline: `Transform your writing in seconds. Select a template, paste your text, get a polished result — no copy-pasting between tools.`
- CTA: `<a href="/accounts/login/" class="btn btn-primary btn-lg">Get started</a>`

Tagline text is easy to adjust directly in the template after implementation.

### Success Criteria

#### Automated Verification

- `uv run pytest tests/test_generate.py` passes (landing template renders without 500)
- `uv run ruff check .` passes (no Python linting concerns; template is HTML only)

#### Manual Verification

- Anonymous `GET /` shows full-viewport dark page with headline, tagline, and "Get started" button
- Clicking "Get started" leads to `/accounts/login/`
- No navbar or app nav links visible on the landing page
- Page renders correctly in a desktop browser

**Implementation Note:** After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Test Updates

### Overview

Fix the two broken assertions and add two new tests covering the landing page and authenticated home behaviour.

### Changes Required

#### 1. Fix test_unauthenticated_redirects_to_login

**File:** `tests/test_auth.py`

**Intent:** The test name and assertion both reflect the old behaviour (302 redirect). Update the test to reflect the new behaviour: anonymous `GET /` returns 200 and renders the landing page. Rename to `test_unauthenticated_sees_landing_page`.

**Contract:** `response.status_code == 200`; assert `b"Get started"` (or similar landing-page-specific content) in `response.content`. Remove the redirect assertion.

#### 2. Fix test_generate_page_requires_login

**File:** `tests/test_generate.py`

**Intent:** This test name implies anonymous access is blocked, but the new behaviour is that anonymous users see the landing page (200). Update the test to verify the landing page is served instead. Rename to `test_anonymous_home_shows_landing_page`.

**Contract:** `response.status_code == 200`; assert landing-specific content (e.g. `b"Get started"`) is present; assert no `id="generate-btn"` in the response (the generate UI is not served to anonymous users).

#### 3. Add test for authenticated home

**File:** `tests/test_generate.py`

**Intent:** Add an explicit smoke test confirming that authenticated `GET /` still serves the generate UI. Complements the landing page test and makes the auth-dispatch contract explicit.

**Contract:** New test `test_authenticated_home_shows_generate_ui`: log in, `GET /`, assert `response.status_code == 200`, assert `b'id="generate-btn"'` in `response.content`.

### Success Criteria

#### Automated Verification

- `uv run pytest` passes (all tests, no failures or unexpected skips)
- `uv run ruff check .` passes
- `uv run ruff format .` produces no diff

#### Manual Verification

- All 3 test files (`test_auth.py`, `test_generate.py`) show green in pytest output
- No other tests broken by the view/routing change

---

## Testing Strategy

### Unit Tests

- `test_anonymous_home_shows_landing_page` (in both test files — one covers auth flow, one covers generate module)
- `test_authenticated_home_shows_generate_ui`

### Manual Testing Steps

1. Start dev server: `uv run manage.py runserver`
2. Visit `http://localhost:8000/` without logging in — verify dark hero page, no app nav
3. Click "Get started" — verify redirect to login form
4. Log in — verify `LOGIN_REDIRECT_URL = "/"` still takes you to the generate UI
5. Visit `http://localhost:8000/` while logged in — verify generate UI loads, no landing page
6. Log out — verify `LOGOUT_REDIRECT_URL = "/accounts/login/"` still works

## Migration Notes

No migrations needed — no model changes.

## References

- Roadmap slice: `context/foundation/roadmap.md` → S-04
- Base template: `templates/base.html`
- Existing generate view: `core/views.py` (GenerateView)
- Existing tests: `tests/test_auth.py`, `tests/test_generate.py`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: View and Routing Change

#### Automated

- [ ] 1.1 `uv run pytest tests/test_generate.py tests/test_auth.py` passes *(verifiable after Phase 2)*
- [x] 1.2 `uv run ruff check .` passes — d670c20
- [x] 1.3 `uv run ruff format .` produces no diff — d670c20

#### Manual

- [ ] 1.4 Anonymous `GET /` returns 200 (landing page, no app nav links) *(verifiable after Phase 2)*
- [ ] 1.5 Authenticated `GET /` returns generate UI unchanged
- [ ] 1.6 No regression in generate-related tests

### Phase 2: Landing Page Template

#### Automated

- [x] 2.1 `uv run pytest tests/test_generate.py` passes (no 500 from missing template)
- [x] 2.2 `uv run ruff check .` passes

#### Manual

- [x] 2.3 Anonymous `GET /` shows full-viewport dark hero with headline, tagline, "Get started" button
- [x] 2.4 "Get started" leads to `/accounts/login/`
- [x] 2.5 No navbar or app nav links on landing page

### Phase 3: Test Updates

#### Automated

- [ ] 3.1 `uv run pytest` passes (full suite, no failures)
- [ ] 3.2 `uv run ruff check .` passes
- [ ] 3.3 `uv run ruff format .` produces no diff

#### Manual

- [ ] 3.4 All updated and new tests show green in pytest output
