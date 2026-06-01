# Auth Scaffold — Plan Brief

> Full plan: `context/changes/auth-scaffold/plan.md`

## What & Why

Wire Django's built-in authentication so every app view requires a login. This is the foundation all other slices depend on — nothing in S-01, S-02, or S-03 can be built without a working auth layer. A protected placeholder home page is included to verify the end-to-end flow without waiting for real UI to exist.

## Starting Point

Django 6.0.5 is installed with auth middleware active but no login views, no templates, and no redirect settings. `urls.py` contains only the admin route. Navigating to any protected URL would currently return a 404.

## Desired End State

Unauthenticated access to any app URL redirects to a login page. A user with valid credentials can log in, land on a protected "Hello, {username}" placeholder page, and log out. Three automated tests verify this behaviour on every future commit.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
|---|---|---|
| Login identifier | Username (Django default) | No custom auth backend needed; username works fine for a solo app and the single-user MVP. |
| Template location | Project-level `templates/` dir | Single template root; add `BASE_DIR / "templates"` to `DIRS` — no app-split overhead. |
| CSS framework | Bootstrap 5 via CDN | Usable form styling across all future pages with no build tooling. |
| Post-login destination | Protected placeholder at `/` | Avoids the default `/accounts/profile/` 404 and provides an immediate end-to-end test. |
| Test coverage | 3 minimal functional tests | Covers redirect, valid login, and invalid login — enough to catch config regressions. |

## Scope

**In scope:** Auth settings, login/logout URL wiring, protected home placeholder, base template with Bootstrap CDN, login template, pytest config, 3 functional tests.

**Out of scope:** Email-as-username login, password reset, OAuth, custom User model (F-02), any real app UI.

## Architecture / Approach

Use `django.contrib.auth.urls` directly — no custom auth views needed. Add a single `korpotron/views.py` with a `home` view decorated `@login_required`. Three settings constants (`LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`) ensure redirects land on real pages. Logout is POST-only in Django 6; the base template includes a form for this.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Auth wiring | Settings + URLs + placeholder view | Low — pure Django config |
| 2. Templates | Renderable login page + home placeholder | Low — straightforward HTML |
| 3. Tests | 3 functional tests + pytest config | Low — thin wrapper around Django test client |

**Prerequisites:** `.env` file with `SECRET_KEY` and `ALLOWED_HOSTS` set (see `.env.example`); `uv run manage.py migrate` applied.
**Estimated effort:** ~1 session across 3 phases.

## Open Risks & Assumptions

- Django's built-in User model is assumed throughout; if F-02 later introduces a custom `AbstractUser`, `views.py` import paths remain unchanged but `User.objects.create_user` in tests may need updating.
- Bootstrap CDN adds an external HTTP dependency on first page load; acceptable for MVP.

## Success Criteria (Summary)

- `uv run manage.py check` and `ruff check .` pass
- Manual browser flow (redirect → login → home → logout) works end-to-end
- `pytest` passes with all 3 tests green
