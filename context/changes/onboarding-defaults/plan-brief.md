# Onboarding Defaults — Plan Brief

> Full plan: `context/changes/onboarding-defaults/plan.md`

## What & Why

New users land on a blank Generate page and must configure templates and option groups before the app is usable — a cold-start friction problem. This change seeds each new user's account with 3 default templates and 3 option groups on first login. Content is defined in a repo JSON fixture so it can be updated without code changes.

## Starting Point

`Template`, `OptionGroup`, and `Option` models exist with user-FK ownership. The login flow uses Django's built-in `user_logged_in` signal and the `CoreConfig` app config is already present but has no `ready()` override.

## Desired End State

A new user logs in and immediately sees 3 ready-to-use templates (Corporate Email, Teams/IM Message, Peer Feedback) and 3 option groups (Language, Tone, Corporate Buzzword Level) on the Generate page. Users who delete their defaults and log back in are not re-seeded. Users who had content before this feature shipped are never touched.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Seeding trigger | `user_logged_in` Django signal | Fires on all login paths without coupling to any view; connected in `CoreConfig.ready()` | Plan |
| "Was ever seeded" tracking | New `OnboardingState` model (OneToOneField to User) | Count-only check can't distinguish "never seeded" from "seeded then deleted"; a persistent row survives deletion | Plan |
| Idempotency check | `OnboardingState` exists OR user has any Template/OptionGroup | Two conditions: `OnboardingState` handles the delete-then-login case; content check handles pre-feature users | Plan |
| Atomicity | `transaction.atomic()`, `OnboardingState` created last | Mid-seed failure leaves user unseeded and safely retryable on next login | Plan |
| Fixture loading | Plain `pathlib` + `json`, not `manage.py loaddata` | Simpler than Django fixture machinery; no management command needed at runtime | Plan |
| Email template title | `generate_title=True` for Corporate Email only | Subject line is natural for email; title field is unnatural for IM and peer feedback | Plan |
| Fixture content | Dummy placeholders | User will author actual prompt text directly in the JSON before shipping | Plan |

## Scope

**In scope:**
- `OnboardingState` model + migration
- `core/fixtures/onboarding_defaults.json` (placeholder content)
- Signal handler in `core/apps.py`
- 4 tests in `tests/test_onboarding.py`

**Out of scope:**
- Actual prompt/instruction text (user authors in the fixture)
- Switching to `AbstractUser` custom user model (deferred)
- Any onboarding UI, welcome messages, or tooltips
- Management command for bulk-seeding existing users

## Architecture / Approach

On `user_logged_in` signal: check `OnboardingState.objects.filter(user=user).exists()` (skip if true) then check if user has any Template or OptionGroup (skip if true). If both checks pass, read `core/fixtures/onboarding_defaults.json`, create all Templates and OptionGroups+Options, then create `OnboardingState` — all inside `transaction.atomic()`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. OnboardingState model | New model + migration for seed-tracking | Migration must depend on `0004_dailygenerationcount` |
| 2. Fixture file | JSON file with correct structure, dummy content | Wrong key names would cause a KeyError at seed time |
| 3. Signal handler | Live seeding on first login, idempotency guard | Model imports inside `ready()` must use lazy pattern to avoid app registry errors |
| 4. Tests | 4 scenarios incl. delete-then-login | Signal fired via `user_logged_in.send()` — confirm handler is connected before tests run |

**Prerequisites:** Migrations from Phase 1 must be applied before Phase 3 can be tested manually.
**Estimated effort:** ~1 session across 4 phases.

## Open Risks & Assumptions

- Fixture content is placeholder — the app is deployable but practically useful only after the user fills in actual prompts.
- Admin login also triggers the signal; the idempotency check (two conditions) makes this harmless but it's a minor overhead on every admin login.

## Success Criteria (Summary)

- Fresh user login → 3 templates and 3 option groups visible on Generate page
- Deleting all content + re-login → no re-seeding (Generate page shows "no templates" message)
- `uv run pytest` passes across all 4 new test scenarios and the existing suite
