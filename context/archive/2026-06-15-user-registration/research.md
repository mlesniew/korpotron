---
date: "2026-06-15T18:51:55Z"
researcher: "Claude Sonnet 4.6"
git_commit: "e0ed756582fb05b53533284a5dbbbd4436af463f"
branch: "master"
repository: "mlesniew/korpotron"
topic: "User registration abuse-prevention: alternatives to admin approval"
tags: [research, auth, registration, abuse-prevention, rate-limiting]
status: complete
last_updated: "2026-06-15"
last_updated_by: "Claude Sonnet 4.6"
---

# Research: User registration abuse-prevention — alternatives to admin approval

**Date**: 2026-06-15T18:51:55Z **Researcher**: Claude Sonnet 4.6 **Git Commit**:
e0ed756582fb05b53533284a5dbbbd4436af463f **Branch**: master **Repository**: mlesniew/korpotron

## Research Question

The roadmap (S-11) specifies admin approval for new accounts to prevent abuse — spam, bots, and unexpected LLM cost
spikes. The underlying goal is access control and cost protection, not necessarily the specific mechanism of admin
approval. What simpler alternatives exist that are common in Django apps, and which is best suited to Korpotron's actual
threat model?

## Summary

The primary cost-protection mechanism already exists: `DAILY_GENERATION_LIMIT` (default 100) is enforced atomically per
user per day in `core/views.py:generate_api`. This caps the per-user blast radius and is already in production. The
remaining risk from open registration is _total account volume × limit_, not per-account abuse.

**Recommended alternative: registration passphrase (shared secret).** An env-var secret required at registration time
eliminates the account-creation risk entirely, with zero dependencies, zero new models, zero ongoing admin work, and ~80
lines of implementation. Email verification is the more robust public-internet answer but requires SMTP infrastructure
that does not exist in this project. Admin approval has the highest protection but the highest ongoing overhead, which
is a poor fit for a solo tool where the admin is the primary user.

The second-best option for minimal friction is **open registration with the existing generation limit as the sole cost
guard** — acceptable if the app URL is not publicly advertised and the tail risk of bot volume is considered acceptable.

## Detailed Findings

### Existing cost-control mechanism (already shipped)

`DAILY_GENERATION_LIMIT` is read from env as `int`, defaulting to `100` (`settings.py:131`). The `generate_api` view
(`views.py:158–250`) enforces it with a `select_for_update` atomic transaction on `DailyGenerationCount` — a
`(user, date)` pair with a running integer count. The `LIMIT = 0` path is explicitly unlimited (`views.py:218`).

This means **per-user cost is already hard-capped**. The threat model for registration gating is narrowed to: preventing
so many accounts from being created that (N users × 100 generations × cost/call) exceeds budget. For a personal tool
with a handful of real users, this is a low-probability risk even with open registration — but it is non-zero for a
publicly-accessible URL.

### Installed packages (from pyproject.toml)

No auth library is installed. The full dependency list is: `dj-database-url`, `django`, `gunicorn`, `openai`,
`psycopg2-binary`, `python-dotenv`, `whitenoise`.

No `django-allauth`, `django-registration`, `django-ratelimit`, or email library. Any new approach must either work with
the stdlib + Django builtins, or add one small package.

### Email / SMTP status

No `EMAIL_BACKEND`, `EMAIL_HOST`, or any `EMAIL_*` setting exists in `settings.py`. SMTP is fully unconfigured. Email
verification would require adding transactional email infrastructure to Fly.io (new secrets, external service account)
before writing a single line of application code.

### Cache backend

No `CACHES` setting is configured. Django's default `LocMemCache` is in effect — in-process, per-worker, resets on
restart. For IP-rate limiting across gunicorn's two workers (`Dockerfile:31`), `LocMemCache` provides per-worker
accounting only. A database-backed cache would share state but requires one management command to initialise; Redis
would require a new Fly service. For a solo tool this imprecision is acceptable.

### Fly.io proxy and IP headers

Fly.io's anycast edge terminates TLS and forwards traffic; `REMOTE_ADDR` as seen by Django is the Fly edge node, not the
real client. Real client IP arrives in `X-Forwarded-For`. Trusting that header requires validating it comes from Fly's
own edge (configurable via `SECURE_PROXY_SSL_HEADER` and trusted-proxy lists) — adds minor but non-trivial complexity to
any IP-based rate-limiting approach.

## Approaches Evaluated

### 1. Registration passphrase / shared secret

A `CharField` on the registration form validated against `settings.REGISTRATION_PASSPHRASE` (an env var). No match →
`ValidationError`; the user is never created. The passphrase is never stored in the database.

- **Dependencies**: none
- **New models / migrations**: none
- **Implementation**: ~80 lines — one `UserRegistrationForm(UserCreationForm)` subclass with a `clean_passphrase()`
  method, one env-var setting, one `RegisterView`, one template
- **Cost protection**: excellent — no account is created without the passphrase
- **UX**: one extra field; instant activation on success; passphrase shared out-of-band (Slack, email, word of mouth)
- **Admin overhead**: none after `fly secrets set REGISTRATION_PASSPHRASE=…`
- **Django idiom**: well-understood pattern for invite-only / internal tools; not a named feature but appears widely in
  tutorials and real codebases
- **Weakness**: a leaked passphrase allows unlimited signups until rotated; rotation is one `fly secrets set` command

### 2. Open registration + rely on existing generation limit

No gate on registration; any visitor creates a fully active account immediately. Cost is bounded by
`DAILY_GENERATION_LIMIT × number_of_accounts`.

- **Dependencies**: none
- **New models / migrations**: none
- **Implementation**: ~50 lines — `RegisterView` with plain `UserCreationForm`, one URL, one template
- **Cost protection**: bounded but not zero — risk = volume × limit × cost/call. With `LIMIT = 100`, each account costs
  at most 100 calls/day regardless of behaviour
- **UX**: best possible — frictionless, instant
- **Admin overhead**: none
- **Django idiom**: the default Django pattern (`UserCreationForm` creates an active user)
- **Weakness**: accepts the tail risk of bot farms creating many accounts. Acceptable if the URL is not publicly indexed
  or advertised

### 3. Email verification

Create user with `is_active=False`; send activation link using `django.core.signing` or `PasswordResetTokenGenerator`
(the same mechanism as built-in password reset). `ActivateView` sets `is_active=True` on valid token.

- **Dependencies**: SMTP infrastructure (not currently configured)
- **New models / migrations**: none (`is_active` is already on `AbstractBaseUser`)
- **Implementation**: ~120 lines — custom token generator, `RegisterView` + `ActivateView`, activation email template,
  two URL patterns. Plus: external SMTP service, Fly secrets for credentials
- **Cost protection**: good — phantom accounts never activate; bots need inbox access to complete registration
- **UX**: requires real email, inbox check, and link click; if email lands in spam, user is stuck
- **Admin overhead**: none after initial SMTP setup
- **Django idiom**: the most common pattern for public Django apps; `django-allauth` and `django-registration` both
  implement this
- **Blocker**: SMTP is unset — this approach requires resolving email infrastructure first

### 4. IP-based rate limiting on registration endpoint

Per-IP counter in Django cache; reject requests above threshold (e.g., 5/hour). Uses `django.core.cache.cache.get/set`.

- **Dependencies**: none for basic implementation; `django-redis` if shared-state across workers is needed
- **New models / migrations**: none
- **Implementation**: ~30 lines — `get_client_ip()` utility + rate-check in `RegisterView.post()`
- **Cost protection**: marginal as standalone; stops naive single-IP bots; ineffective against distributed bots or VPN
  rotation
- **UX**: zero impact for normal users
- **Admin overhead**: none
- **Fly.io caveat**: `REMOTE_ADDR` is the Fly edge IP; must parse `X-Forwarded-For` with appropriate trust
  configuration. Two gunicorn workers share no cache state with `LocMemCache`
- **Django idiom**: common secondary hardening; `django-ratelimit` is the canonical package but not required for a
  simple implementation
- **Best used as**: a secondary layer on top of approach 1 or 2, not as a primary gate

### 5. CAPTCHA

hCaptcha or reCAPTCHA widget on the form. On POST, Django validates the response token against the provider's API before
creating the user.

- **Dependencies**: `django-hcaptcha` or `django-recaptcha` + external service account (free tier available)
- **New models / migrations**: none
- **Implementation**: ~15 lines (with the package) — field in form, widget in template, two env vars
- **Cost protection**: moderate — deters automated bots; CAPTCHA-solving services can bypass it; does not cap per-user
  cost
- **UX**: CAPTCHA friction; accessibility concerns; external JS dependency
- **Admin overhead**: none
- **Django idiom**: common for public forms; overkill for a private personal tool
- **Weakness**: external service uptime/latency at registration time; solving services exist for all major CAPTCHA
  providers

### 6. Admin approval (current plan — baseline)

Create user with `is_active=False`; admin visits Django Admin and sets `is_active=True` manually.

- **Dependencies**: none (`django.contrib.admin` already in `INSTALLED_APPS`)
- **New models / migrations**: none
- **Implementation**: ~40 lines — `RegisterView` with `is_active=False` in `form_valid`, pending template
- **Cost protection**: perfect — no account is ever active without explicit action
- **UX**: worst — user waits indefinitely; admin may be unavailable; no notification mechanism (no SMTP)
- **Admin overhead**: highest — manual action per user; grows linearly with signups
- **Django idiom**: common for B2B waitlists and enterprise tools; not appropriate when admin is also the primary user
  of the tool

## Code References

- `korpotron/settings.py:131` — `DAILY_GENERATION_LIMIT = int(os.environ.get("DAILY_GENERATION_LIMIT", "100"))`
- `core/views.py:158–250` — `generate_api` with full per-user daily rate-limit enforcement
- `core/models.py:71–84` — `DailyGenerationCount` model (`user`, `date`, `count`)
- `pyproject.toml:6–13` — installed dependencies (no auth library, no SMTP library)
- `.env.example:1–14` — documented env vars (no EMAIL\_\* vars present)
- `Dockerfile:27` — `--workers 2` gunicorn; two-worker deployment affects `LocMemCache` usefulness

## Architecture Insights

**The daily generation limit is load-bearing for cost control.** It is already implemented correctly with row-level
locking and covers the per-user blast radius. Any registration gating approach only needs to address the
_account-creation volume_ risk, not the per-user usage risk.

**The passphrase approach fits the project's constraints best:**

- Zero dependencies (project has a preference for minimal deps — pyproject.toml is lean)
- Zero migrations (the project has invested in a clean model schema)
- Operational: one Fly secret to set and potentially rotate
- Implementation: entirely in `core/forms.py` and `core/views.py`, following established patterns

**Email verification is the right long-term answer** if the app ever becomes public-facing and SMTP infrastructure is
set up. The implementation would closely mirror Django's built-in `PasswordResetView`/`PasswordResetConfirmView` token
flow — good to note for future reference.

**IP rate limiting on Fly.io requires `X-Forwarded-For` parsing.** Fly.io injects the real client IP as the first
untrusted `X-Forwarded-For` value; the correct extraction is
`request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()`. Django's `USE_X_FORWARDED_HOST` is for the Host
header, not the client IP. A small `get_client_ip()` utility is needed.

## Historical Context (from prior changes)

- `context/archive/2026-06-04-daily-generation-limit/` — S-05 implementation. Established the `DailyGenerationCount`
  model and the `select_for_update` pattern. This is the primary cost guardrail that makes the registration threat model
  manageable.
- Roadmap S-11 note: "No email notifications — admin must check the Django admin panel to discover pending
  registrations." This signals that SMTP was explicitly not set up even for admin notification, reinforcing that email
  verification requires new infrastructure.

## Open Questions

1. **Is the app URL publicly indexed / advertised?** If not, open registration + generation limit may be sufficient. If
   yes, a passphrase gate is the minimal additional protection.
2. **What is the acceptable tail cost risk?** With `LIMIT=100` and e.g. 1,000 bot accounts, the daily cost exposure is
   100,000 calls. At typical OpenRouter pricing this may be negligible or significant depending on the model used.
   Quantifying this informs whether open registration is acceptable.
3. **Is SMTP infrastructure planned for any other feature?** If so, email verification becomes free to add once SMTP is
   wired. If not, it is a separate infrastructure investment not justified by registration alone.
4. **Passphrase rotation UX**: if the passphrase leaks, rotating it invalidates all future use of the old passphrase.
   There is no per-invitee revocation — the whole credential changes. Is this acceptable?
