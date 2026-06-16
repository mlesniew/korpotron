# User Registration — Plan Brief

> Full plan: `context/changes/user-registration/plan.md` Research: `context/changes/user-registration/research.md`

## What & Why

Add self-registration to Korpotron so users can create their own accounts without admin intervention. Access is gated by
a shared passphrase (`REGISTRATION_PASSPHRASE` env var) — no account is created without it. The passphrase approach was
selected because it requires zero new dependencies, zero migrations, and zero ongoing admin work, while the existing
daily generation limit already bounds per-user cost.

## Starting Point

The app has a complete login/logout scaffold (`django.contrib.auth.urls` at `/accounts/`) but no registration endpoint.
A custom-styled standalone login template (`templates/registration/login.html`) sets the visual standard the register
page must match.

## Desired End State

A `/register/` form (username, password, confirm password, passphrase) that creates an immediately-active account and
redirects to the login page. "Register" links appear on the landing page nav and on the login page. The endpoint returns
403 when `REGISTRATION_PASSPHRASE` is not configured.

## Key Decisions Made

| Decision                   | Choice                     | Why (1 sentence)                                                                                                  | Source   |
| -------------------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------- |
| Abuse-prevention mechanism | Passphrase gate            | Zero deps, zero migrations, easy rotation — fits a personal tool better than admin approval or email verification | Research |
| Unset passphrase behavior  | Block (403)                | Missing env var is a deployment gap, not an invitation to open access                                             | Plan     |
| Post-registration flow     | Redirect to login          | Keeps auth concerns separated; no auto-login complexity                                                           | Plan     |
| Email field                | Dropped                    | Not needed for a personal tool; no SMTP, no verification — username-only is simpler                               | Review   |
| Template approach          | Mirror login.html manually | Standalone pages (not extending base.html) is the established pattern                                             | Plan     |

## Scope

**In scope:**

- `UserRegistrationForm` subclassing `UserCreationForm` with passphrase validation
- `RegisterView` with 403-guard when passphrase unset
- `/register/` URL in `core/urls.py`
- `templates/registration/register.html` matching login.html's dark theme
- "Register" links on landing page and login page
- Post-registration success notice on login page (Django messages)
- `REGISTRATION_PASSPHRASE` setting + `.env.example` entry
- Test suite (5 scenarios)

**Out of scope:**

- Email verification (no SMTP)
- Admin approval
- Rate limiting on registration
- Auto-login after registration
- Per-user passphrase or invite tokens

## Architecture / Approach

Thin form subclass (`UserRegistrationForm`) in `core/forms.py` with `clean_passphrase()` validating against
`settings.REGISTRATION_PASSPHRASE`. A `FormView` (`RegisterView`) in `core/views.py` checks the setting in `dispatch()`
before rendering or processing. All code goes into existing files except one new template and one new test file.

## Phases at a Glance

| Phase                | What it delivers                                | Key risk                                                  |
| -------------------- | ----------------------------------------------- | --------------------------------------------------------- |
| 1. Backend           | Form, view, URL, settings entry, .env.example   | Passphrase logic or 403-guard wrong                       |
| 2. Template          | register.html matching login page style         | 5-field layout diverging from login.html's visual pattern |
| 3. Nav links + tests | Register links, success notice, full test suite | Existing tests broken by URL or import changes            |

**Prerequisites:** F-01 (auth scaffold) — already shipped **Estimated effort:** ~1 session across 3 phases (~100 lines
of code + 1 template)

## Open Risks & Assumptions

- A leaked passphrase allows unlimited signups until rotated via `fly secrets set` — acceptable for a personal tool
- `base.html` does not render Django messages; success notice must be added explicitly to `login.html` in Phase 3

## Success Criteria (Summary)

- `/register/` with correct passphrase creates an active user and lands the user on the login page with a success notice
- `/register/` with passphrase unset returns 403
- All existing tests continue to pass; Docker build succeeds
