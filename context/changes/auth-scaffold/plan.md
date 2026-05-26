# Auth Scaffold Implementation Plan

## Overview

Wire Django's built-in authentication into the Korpotron scaffold. After this slice, users can log in and out with username + password, every app view is protected by `login_required`, and a protected placeholder home page confirms the end-to-end login flow works.

## Current State Analysis

Django 6.0.5 is installed with `django.contrib.auth` in `INSTALLED_APPS` and `AuthenticationMiddleware` in `MIDDLEWARE` (`settings.py:30,43`). No custom apps exist. `urls.py:20-22` contains only the admin route. `TEMPLATES[0]["DIRS"]` is empty (`settings.py:53`) — no templates have been created. No `LOGIN_URL`, `LOGIN_REDIRECT_URL`, or `LOGOUT_REDIRECT_URL` are set, so Django's defaults point at `/accounts/profile/` (a 404).

## Desired End State

A user navigating to any protected URL is redirected to `/accounts/login/`. After a successful login they land on a protected placeholder home page (`/`) that greets them by username. A logout button on that page posts to `/accounts/logout/` and returns them to the login page. All three behaviours are covered by automated tests.

### Key Discoveries

- `settings.py:53` — `DIRS: []`; need to add `BASE_DIR / "templates"` so project-level templates are found
- `settings.py:75-80` — password validators already configured; no changes needed
- `urls.py:17-22` — only `admin/` route; `include` not yet imported
- `pyproject.toml` — no `[tool.pytest.ini_options]` block; `DJANGO_SETTINGS_MODULE` must be added for pytest-django to work
- Django 5+ / 6 — `LogoutView` only accepts POST requests; logout must be triggered by a form, not a link

## What We're NOT Doing

- Custom auth backend for email-as-username (using Django's default username field)
- OAuth / social login (parked per roadmap)
- Custom `AbstractUser` model (F-02 owns data model; this slice uses Django's built-in `User`)
- Password reset flow (not needed for MVP with a single user)
- Any styling beyond Bootstrap 5 CDN in a base template

## Implementation Approach

Use Django's built-in `django.contrib.auth.urls` for all auth routes — no custom views needed. Add a single `korpotron/views.py` with a `home` view protected by `@login_required`. Configure settings and create three templates (base, login, home). The only non-obvious item is the POST-only logout requirement in Django 6.

## Phase 1: Auth wiring — settings, URLs, and placeholder view

### Overview

Configure the settings Django needs to redirect correctly, wire auth routes into the main URL conf, and add the protected placeholder view. After this phase the app logic is complete; it just lacks templates.

### Changes Required

#### 1. Settings — templates dir and auth redirects

**File**: `korpotron/settings.py`

**Intent**: Tell Django where to find project-level templates, and explicitly set auth redirect targets so no request lands on a missing URL.

**Contract**:
- `TEMPLATES[0]["DIRS"]` → `[BASE_DIR / "templates"]`
- Add three constants after the existing `AUTH_PASSWORD_VALIDATORS` block:
  `LOGIN_URL`, `LOGIN_REDIRECT_URL = "/"`, `LOGOUT_REDIRECT_URL`

#### 2. URL conf — auth routes and home

**File**: `korpotron/urls.py`

**Intent**: Expose Django's built-in login/logout endpoints and register the home route.

**Contract**:
- Add `include` to the `django.urls` import
- Add `from korpotron import views`
- Prepend `path("accounts/", include("django.contrib.auth.urls"))` and `path("", views.home, name="home")` to `urlpatterns`

#### 3. Placeholder home view

**File**: `korpotron/views.py` (new)

**Intent**: Provide a protected landing page that confirms login_required is enforced.

**Contract**: `home(request: HttpRequest) -> HttpResponse` decorated with `@login_required`, renders `home.html`. Type hints required (project convention).

### Success Criteria

#### Automated Verification

- `uv run manage.py check` exits 0 with no errors
- `ruff check .` exits 0

#### Manual Verification

- `uv run manage.py runserver` starts without error
- Navigating to `http://localhost:8000/` redirects to the login page (no 404 or 500)

**Implementation Note**: After completing this phase and automated checks pass, confirm the manual redirect behaviour before moving to Phase 2.

---

## Phase 2: Templates

### Overview

Create the three templates that make the auth flow usable in a browser: a base layout with Bootstrap 5, the login form, and the placeholder home page.

### Changes Required

#### 1. Base template

**File**: `templates/base.html` (new)

**Intent**: Provide a minimal shared layout with Bootstrap 5 loaded from CDN, a `{% block content %}` extension point, and a logout button that posts to the built-in logout URL.

**Contract**: The logout button must be inside a `<form method="post" action="{% url 'logout' %}">{% csrf_token %}` — a plain anchor tag will not work because `LogoutView` rejects GET requests in Django 6. Only render the logout form when `user.is_authenticated`.

#### 2. Login template

**File**: `templates/registration/login.html` (new)

**Intent**: Render Django's built-in `AuthenticationForm` in the base layout.

**Contract**: Extend `base.html`. Render `{{ form.as_p }}` wrapped in `<form method="post">{% csrf_token %}`. The `LoginView` passes `form` to this template automatically.

#### 3. Home template

**File**: `templates/home.html` (new)

**Intent**: Placeholder page shown after login, confirms the authenticated user landed correctly.

**Contract**: Extend `base.html`. Display `Hello, {{ user.username }}!` and a brief "placeholder" note. The `user` variable is available automatically via the `django.contrib.auth.context_processors.auth` context processor already configured in `settings.py:58`.

### Success Criteria

#### Manual Verification

- Login page renders at `http://localhost:8000/accounts/login/` with a username/password form
- Submitting valid credentials redirects to `http://localhost:8000/` and shows the username greeting
- Unauthenticated `GET /` redirects to `/accounts/login/`
- Clicking Logout returns to the login page

**Implementation Note**: Confirm all four manual steps pass before moving to Phase 3.

---

## Phase 3: Tests

### Overview

Add pytest-django configuration and three functional tests that verify the critical auth behaviours automatically.

### Changes Required

#### 1. Pytest configuration

**File**: `pyproject.toml`

**Intent**: Tell pytest-django which settings module to use so tests can run without a separate `conftest.py` or env var.

**Contract**: Add a `[tool.pytest.ini_options]` section with `DJANGO_SETTINGS_MODULE = "korpotron.settings"`.

#### 2. Functional auth tests

**File**: `tests/test_auth.py` (new)

**Intent**: Verify the three critical auth behaviours: unauthenticated access redirects to login, valid login lands on home, invalid credentials returns the form with an error.

**Contract**: Three test functions, each decorated `@pytest.mark.django_db`, using Django's `Client`. Create a test user via `User.objects.create_user(username="tester", password="pass1234")`.

- `test_unauthenticated_redirects_to_login` — `client.get("/")` → status 302, `Location` starts with `/accounts/login/`
- `test_valid_login_redirects_to_home` — `client.post("/accounts/login/", {...}, follow=True)` → status 200, final URL is `/`
- `test_invalid_login_returns_form` — `client.post("/accounts/login/", {wrong password})` → status 200 (form re-rendered with error)

### Success Criteria

#### Automated Verification

- `pytest` exits 0 with all 3 tests passing
- `ruff check .` exits 0 on the new test file

---

## Testing Strategy

### Unit Tests

Not applicable — this slice has no business logic beyond delegation to Django's built-in auth.

### Integration Tests (Phase 3)

- Unauthenticated redirect
- Valid credential login → home
- Invalid credential rejection

### Manual Testing Steps

1. Start dev server: `uv run manage.py runserver`
2. Open `http://localhost:8000/` — confirm redirect to login
3. Log in with a superuser (create one: `uv run manage.py createsuperuser`)
4. Confirm landing on the home placeholder with username displayed
5. Click Logout — confirm return to login page
6. Attempt `http://localhost:8000/` again while logged out — confirm redirect

## Migration Notes

No new models in this slice. `uv run manage.py migrate` applies the existing `django.contrib.auth` migrations (already provided by Django); no new migrations to create.

## References

- Roadmap: `context/foundation/roadmap.md` (F-01, lines 61–72)
- PRD Access Control: `context/foundation/prd.md` (line 100)
- Settings: `korpotron/settings.py`
- URL conf: `korpotron/urls.py`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Auth wiring — settings, URLs, and placeholder view

#### Automated

- [ ] 1.1 `uv run manage.py check` exits 0
- [ ] 1.2 `ruff check .` exits 0

#### Manual

- [ ] 1.3 Dev server starts without error
- [ ] 1.4 `GET /` redirects to login page (no 404 or 500)

### Phase 2: Templates

#### Manual

- [ ] 2.1 Login page renders at `/accounts/login/` with form
- [ ] 2.2 Valid login redirects to `/` with username greeting
- [ ] 2.3 Unauthenticated `GET /` redirects to `/accounts/login/`
- [ ] 2.4 Logout returns to login page

### Phase 3: Tests

#### Automated

- [ ] 3.1 `pytest` exits 0, all 3 tests passing
- [ ] 3.2 `ruff check .` exits 0 on test file
