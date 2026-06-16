# User Registration Implementation Plan

## Overview

Add self-registration to Korpotron: a `/register/` form gated by a shared passphrase (`REGISTRATION_PASSPHRASE` env
var). Successful registration creates an immediately-active account and redirects to the login page. No new models, no
migrations, no new dependencies.

## Current State Analysis

The app has a complete auth scaffold (login/logout via `django.contrib.auth.urls`) but no registration endpoint. The
daily generation limit (`DAILY_GENERATION_LIMIT`, `settings.py:133`) already caps per-user cost; the passphrase gate is
the only remaining access control needed.

**Key Discoveries:**

- `templates/registration/login.html` — fully custom standalone HTML (does not extend `base.html`); uses `k-login-page`,
  `k-login-card`, `k-login-field`, `k-login-input`, `k-login-submit`, `k-login-error` CSS classes. The registration
  template must match this structure.
- `core/forms.py` — uses `clean_*()` validators on `ModelForm` subclasses; `UserCreationForm` provides `username`,
  `password1`, `password2`; we add `email` (optional) and `passphrase` (never stored).
- `core/views.py` — CBVs only; `FormView` is the right base for `RegisterView`. The `form_valid()` pattern (save +
  redirect) is established.
- `core/urls.py` — registration URL goes here and is automatically mounted at `/register/` by `korpotron/urls.py`.
- `templates/core/landing.html` — has `Log in` link in nav; needs a companion `Register` link.
- No Django messages are currently rendered anywhere; Phase 3 adds message rendering to `login.html` alongside the
  `Register` nav link.

## Desired End State

- `GET /register/` returns 403 if `REGISTRATION_PASSPHRASE` is not set; otherwise renders the registration form.
- A valid form submission (correct passphrase, valid username/password) creates an active user and redirects to
  `/accounts/login/` with a success notice.
- A wrong passphrase leaves the form with a field-level error and no user is created.
- "Register" links appear on the landing page nav and on the login page.

### Key Discoveries (reiterated for implementer):

- `UserCreationForm` does not include `email` by default — it must be declared explicitly as an optional `EmailField`.
- The `passphrase` field must use `PasswordInput` widget so the value is not echoed.
- `reverse_lazy("login")` is the correct success URL — `"login"` is the name registered by `django.contrib.auth.urls`.
- `HttpResponseForbidden` is needed in `RegisterView.dispatch()` when the passphrase env var is unset.
- `base.html` does not render Django messages; the success notice after redirect must be added explicitly to
  `templates/registration/login.html`.

## What We're NOT Doing

- No email field on the registration form — username-only registration (deliberate; email not needed for a personal
  tool)
- No email verification (SMTP not configured; S-11 explicitly excludes it)
- No `is_active=False` / admin approval flow
- No rate limiting on registration (the daily generation limit is the cost guard)
- No auto-login after registration (redirects to login, user logs in manually)
- No per-user passphrase; rotation is a single `fly secrets set` command

## Implementation Approach

Single-phase backend work followed by a styled template, then nav link additions and tests. All code goes into existing
files (`core/forms.py`, `core/views.py`, `core/urls.py`, `korpotron/settings.py`) except for the one new template and
one new test file.

---

## Phase 1: Backend — settings, form, view, URL

### Overview

Add the `REGISTRATION_PASSPHRASE` setting, the `UserRegistrationForm` subclass, a `RegisterView`, and the URL pattern.
This phase has no UI — the view renders a template added in Phase 2.

### Changes Required:

#### 1. Settings entry

**File**: `korpotron/settings.py`

**Intent**: Expose `REGISTRATION_PASSPHRASE` as an optional env var. When unset (empty string), registration is blocked
at the view layer.

**Contract**: Add adjacent to `DAILY_GENERATION_LIMIT` at the bottom of the file:
`REGISTRATION_PASSPHRASE = os.environ.get("REGISTRATION_PASSPHRASE", "")`

#### 2. .env.example entry

**File**: `.env.example`

**Intent**: Document the new variable so developers know it exists.

**Contract**: Append a commented-out entry below `DAILY_GENERATION_LIMIT`:
`# REGISTRATION_PASSPHRASE=  # required to enable self-registration`

#### 3. Registration form

**File**: `core/forms.py`

**Intent**: Subclass `UserCreationForm` to add `passphrase` (validated against the env var, never stored). No email
field — username-only registration. The form is the only place passphrase validation logic lives.

**Contract**: New class `UserRegistrationForm(UserCreationForm)` with:

- `passphrase = CharField(widget=PasswordInput, label="Passphrase")` declared on the class
- `clean_passphrase(self) -> str` raises `ValidationError("Incorrect passphrase.")` when the submitted value does not
  equal `settings.REGISTRATION_PASSPHRASE`
- Import additions: `PasswordInput`, `CharField` from `django.forms`; `settings` from `django.conf`

#### 4. Registration view

**File**: `core/views.py`

**Intent**: A `FormView` that blocks when `REGISTRATION_PASSPHRASE` is unset, saves the user on valid submission, emits
a success message, and redirects to the login page.

**Contract**: New class `RegisterView(FormView)`:

- `template_name = "registration/register.html"`
- `form_class = UserRegistrationForm`
- `success_url = reverse_lazy("login")`
- `dispatch()` returns `HttpResponseForbidden()` if `not settings.REGISTRATION_PASSPHRASE`
- `form_valid()` calls `form.save()`, then `messages.success(self.request, "Account created. You can now log in.")`,
  then `super().form_valid(form)`
- Import additions: `HttpResponseForbidden`, `messages`, `FormView`; `UserRegistrationForm` from `core.forms`

#### 5. URL pattern

**File**: `core/urls.py`

**Intent**: Mount the registration view at `/register/`.

**Contract**: Add `path("register/", RegisterView.as_view(), name="register")` and import `RegisterView`.

### Success Criteria:

#### Automated Verification:

- Linting passes: `uv run ruff check .`

#### Manual Verification:

- `GET /register/` with `REGISTRATION_PASSPHRASE` unset → 403
- `GET /register/` with `REGISTRATION_PASSPHRASE=test` → 200 (may be unstyled until Phase 2 template exists)

**Implementation Note**: Phase 2 can be started before manual verification — the template must exist for the view to
render. Complete Phase 1 code, then create the template in Phase 2, then verify both together.

---

## Phase 2: Registration template

### Overview

Create `templates/registration/register.html` mirroring the structure and styling of `login.html`. Renders all four form
fields manually (matching the hand-crafted HTML pattern), shows non-field errors at the top and field-level errors below
each input.

### Changes Required:

#### 1. Registration template

**File**: `templates/registration/register.html`

**Intent**: A standalone page (not extending `base.html`) styled identically to the login page. Renders: username,
email, password, confirm password, passphrase — each using `k-login-field` / `k-login-lbl` / `k-login-input`. Includes a
"Already have an account? Log in →" footer link.

**Contract**:

- Same page skeleton as `login.html`: `k-login-page` → `k-login-page-inner` → `k-login-card`
- `k-login-card-hdr` with title "Register" and sub "Create an account to access Korpotron."
- Non-field errors rendered in a `k-login-error` div above the field list (same pattern as login error block)
- Each field: `k-login-field` wrapper > `k-login-lbl` label > `k-login-input` input. After each input, if the field has
  errors, render them in a small `<div style="color:oklch(70% 0.2 25);font-size:12px;margin-top:4px">`.
- Field order: username (`type="text"`), password (`type="password"`, `autocomplete="new-password"`), confirm password
  (`type="password"`, `autocomplete="new-password"`), passphrase (`type="password"`)
- Submit button `k-login-submit` with label "Create account"
- Footer link to `{% url 'login' %}`: "Already have an account? Log in →" using `k-login-back` class (same as the
  back-to-home link in login.html)
- Grid overlay `body::before` CSS block identical to login.html (copy verbatim)

### Success Criteria:

#### Automated Verification:

- Linting passes: `uv run ruff check .`
- Tests pass (Phase 3 tests are written against this template): `uv run pytest tests/test_registration.py`

#### Manual Verification:

- `GET /register/` with `REGISTRATION_PASSPHRASE=test` → form renders, matches login page visual style
- Submitting with wrong passphrase → page re-renders with "Incorrect passphrase." error under the passphrase field
- Submitting with mismatched passwords → page re-renders with password mismatch error under password field
- Submitting valid form → redirected to login page

**Implementation Note**: Verify visually after Phase 3 tests pass.

---

## Phase 3: Nav links + tests

### Overview

Add "Register" entry points on the landing page and login page, add a Django messages rendering block to the login page
(so the post-registration success notice is visible), and write the pytest test suite covering the registration flow.

### Changes Required:

#### 1. Landing page nav link

**File**: `templates/core/landing.html`

**Intent**: Add a "Register" CTA alongside the existing "Log in" button so unauthenticated visitors can self-register.

**Contract**: In the nav (`k-landing-nav`), add a "Register" link before the "Log in" link. Use the same
`k-landing-login-btn` class. The link points to `{% url 'register' %}`.

#### 2. Login page — Register link + success notice

**File**: `templates/registration/login.html`

**Intent**: Add a "Register" link below the submit button and add message rendering so the post-registration success
notice is visible after redirect.

**Contract**:

- After `<button type="submit" ...>Log in</button>` add a `<div>` containing a `{% url 'register' %}` link with text
  "Don't have an account? Register →", styled with `k-login-back` or a comparable subtle link style.
- Above the form (or just below the card header), add a messages block:
  `{% if messages %}{% for message in messages %}<div class="k-login-success">{{ message }}</div>{% endfor %}{% endif %}`
  with an inline style or a new minimal `k-login-success` class:
  `color: oklch(75% 0.18 145); font-size: 13px; margin-bottom: 12px;`.

#### 3. Test suite

**File**: `tests/test_registration.py`

**Intent**: Cover the four critical behaviors: unset passphrase blocks, wrong passphrase rejects without creating a
user, valid submission creates an active user and redirects to login, and GET returns 200 when configured.

**Contract**: Five `@pytest.mark.django_db` test functions using the `client: Client` fixture and `settings`
pytest-django fixture:

- `test_register_get_blocked_when_passphrase_unset` — set `settings.REGISTRATION_PASSPHRASE = ""`; `GET /register/` →
  403
- `test_register_post_blocked_when_passphrase_unset` — set `settings.REGISTRATION_PASSPHRASE = ""`; valid POST → 403
- `test_register_get_returns_200` — set `settings.REGISTRATION_PASSPHRASE = "secret"`; `GET /register/` → 200
- `test_register_wrong_passphrase_rejected` — POST with wrong passphrase → 200 (form re-render),
  `User.objects.filter(username="newuser")` does not exist
- `test_register_valid_creates_user_and_redirects` — POST with correct passphrase, valid username/password → 302 to
  `/accounts/login/`, `User.objects.filter(username="newuser").exists()` is True and `user.is_active` is True

### Success Criteria:

#### Automated Verification:

- Tests pass: `uv run pytest tests/test_registration.py -v`
- All existing tests still pass: `uv run pytest`
- Linting passes: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Docker build succeeds: `docker build .`

#### Manual Verification:

- Landing page shows "Register" link in the nav
- Login page shows "Register" link below the submit button
- Full registration flow: visit landing → click Register → fill form with valid passphrase → redirected to login with
  "Account created" notice → log in successfully

---

## Testing Strategy

### Unit Tests:

- Passphrase unset → 403 on GET and POST
- Wrong passphrase → form error, no user created
- Valid passphrase + valid credentials → user created, is_active=True, redirect to login
- GET with passphrase set → 200

### Integration Tests:

- Django `Client` used throughout — no mocking needed for this feature

### Manual Testing Steps:

1. Set `REGISTRATION_PASSPHRASE=testpass` in `.env`
2. Visit landing page — confirm "Register" link appears in nav
3. Click Register — confirm form renders with correct styling
4. Submit with wrong passphrase — confirm error shown, no new user in admin
5. Submit with mismatched passwords — confirm password error shown
6. Submit valid form — confirm redirect to login with success notice
7. Log in with the new credentials — confirm access to the app
8. Unset `REGISTRATION_PASSPHRASE` — confirm `/register/` returns 403

## Migration Notes

No migrations required.

## References

- Related research: `context/changes/user-registration/research.md`
- Auth URL setup: `korpotron/urls.py:22` — `django.contrib.auth.urls` mounts at `/accounts/`
- Daily generation limit (cost guard): `core/views.py:158–250`, `settings.py:133`
- Login template to mirror: `templates/registration/login.html`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Backend — settings, form, view, URL

#### Automated

- [x] 1.1 Linting passes: `uv run ruff check .` — e95bec7

#### Manual

- [x] 1.2 `GET /register/` with `REGISTRATION_PASSPHRASE` unset → 403 — e95bec7
- [x] 1.3 `GET /register/` with `REGISTRATION_PASSPHRASE=test` → 200 (after Phase 2 template) — e95bec7

### Phase 2: Registration template

#### Automated

- [x] 2.1 Linting passes: `uv run ruff check .` — e95bec7
- [x] 2.2 Tests pass: `uv run pytest tests/test_registration.py` — e95bec7

#### Manual

- [x] 2.3 Form renders, matches login page visual style — e95bec7
- [x] 2.4 Wrong passphrase → field error displayed — e95bec7
- [x] 2.5 Mismatched passwords → field error displayed — e95bec7
- [x] 2.6 Valid form → redirected to login page — e95bec7

### Phase 3: Nav links + tests

#### Automated

- [x] 3.1 Tests pass: `uv run pytest tests/test_registration.py -v` — e95bec7
- [x] 3.2 All existing tests pass: `uv run pytest` — e95bec7
- [x] 3.3 Linting passes: `uv run ruff check .` — e95bec7
- [x] 3.4 Format check: `uv run ruff format --check .` — e95bec7
- [x] 3.5 Docker build succeeds: `docker build .` — e95bec7

#### Manual

- [x] 3.6 Landing page shows "Register" link in nav — e95bec7
- [x] 3.7 Login page shows "Register" link and success notice renders after registration — e95bec7
- [x] 3.8 Full end-to-end flow verified (register → login → app access) — e95bec7
