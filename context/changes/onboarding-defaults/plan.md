# Onboarding Defaults Implementation Plan

## Overview

Seed new users with 3 default templates and 3 default option groups on first login so they can immediately use the app without manual setup. Defaults are user-owned and fully editable or deletable. Content lives in a JSON fixture in the repo so it can be updated without touching code.

## Current State Analysis

- `Template`, `OptionGroup`, `Option` models exist with user ownership — no schema changes needed for the seeded data itself.
- `core/apps.py` has a bare `CoreConfig` with no `ready()` override — the signal connection goes here.
- No per-user "was ever seeded" state exists; a new `OnboardingState` model (OneToOneField to User) provides the persistent guard.
- `DailyGenerationCount` in `core/models.py` and its migration `0004_dailygenerationcount.py` are the immediate predecessors — the new migration depends on `0004`.

### Key Discoveries:

- `core/apps.py:CoreConfig` — `ready()` is absent; safe to add without conflict
- `core/models.py` — `Template` and `OptionGroup` use `settings.AUTH_USER_MODEL` FK; `Option` uses a FK to `OptionGroup` (`group = ForeignKey(OptionGroup, ...)`) — no user FK on `Option`
- `tests/conftest.py` — `user` fixture creates `User` via `create_user`; signal tests fire `user_logged_in` manually
- Last migration: `core/migrations/0004_dailygenerationcount.py` — new migration depends on it

## Desired End State

After this plan:
- A user who logs in for the first time lands on the Generate page with 3 usable templates and 3 option groups already configured.
- A user who deletes all their templates and option groups then logs back in does not get re-seeded.
- A user who had content before this feature shipped is never seeded.
- Fixture content can be updated by editing `core/fixtures/onboarding_defaults.json` and redeploying; no code changes required for content edits.
- `uv run pytest` passes across all 4 new test scenarios.

### Key Discoveries:

- `user_logged_in` signal (django.contrib.auth.signals) fires on every login path — admin, form login, future OAuth — so no view coupling needed
- Idempotency guard is two-condition: skip if `OnboardingState` exists (handles delete-then-login) OR if user already has any templates or option groups (handles pre-feature users)
- `OnboardingState` row is created **last** inside `transaction.atomic()` so a mid-seed failure leaves the user unseeded and retryable on next login

## What We're NOT Doing

- Not using `manage.py loaddata` / Django fixture machinery — the JSON is loaded via plain `pathlib`/`json` in the signal handler
- Not adding a `ready()` method that pre-loads fixture data at startup — fixture is read lazily at signal-fire time (rare event, no startup cost worth avoiding)
- Not switching to a custom `AbstractUser` — deferred; `OnboardingState` OneToOneField is sufficient for now
- Not seeding users via a management command or migration data migration — login signal is the specified trigger
- Not displaying any onboarding UI, tooltips, or welcome messages — content seeding only

## Implementation Approach

1. Add `OnboardingState` model + migration (Phase 1)
2. Create JSON fixture with dummy content in the correct shape (Phase 2)
3. Connect `user_logged_in` signal in `CoreConfig.ready()`; signal handler performs two-condition skip check, reads fixture, seeds atomically, and creates `OnboardingState` last (Phase 3)
4. Write 4 targeted tests covering first-login seeding, idempotency on second login, pre-existing-content skip, and delete-then-login no-reseed (Phase 4)

---

## Phase 1: OnboardingState Model and Migration

### Overview

Add a lightweight `OnboardingState` model that records whether a user was ever seeded. Existence of the row is the definitive "was seeded" signal — the row is never deleted even if the user deletes their content.

### Changes Required:

#### 1. OnboardingState model

**File**: `core/models.py`

**Intent**: Add `OnboardingState` with a `OneToOneField` to `settings.AUTH_USER_MODEL` and a `seeded_at` auto-timestamp. Cascade-delete when the user is deleted.

**Contract**: Field names `user` (OneToOneField, CASCADE) and `seeded_at` (DateTimeField, auto_now_add=True). No `__str__` required beyond a basic representation.

#### 2. Migration

**File**: `core/migrations/0005_onboardingstate.py`

**Intent**: Generated via `uv run manage.py makemigrations` after adding the model. Do not hand-write — let Django generate it to ensure field types and dependency on `0004_dailygenerationcount` are correct.

**Contract**: Depends on `("core", "0004_dailygenerationcount")` and `migrations.swappable_dependency(settings.AUTH_USER_MODEL)`.

### Success Criteria:

#### Automated Verification:

- Migration generates cleanly: `uv run manage.py makemigrations --check` passes after generating
- Migration applies cleanly: `uv run manage.py migrate`
- `uv run pytest` — no existing tests broken

#### Manual Verification:

- `OnboardingState` is visible in Django admin (auto-registered via `admin.site.register` or just via admin autodiscovery — confirm it appears)

#### 3. Admin registration

**File**: `core/admin.py`

**Intent**: Register `OnboardingState` with `@admin.register` so it appears in the Django admin for debugging purposes.

**Contract**: `list_display = ["user", "seeded_at"]`.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation that `OnboardingState` is present before proceeding.

---

## Phase 2: Fixture File

### Overview

Create `core/fixtures/onboarding_defaults.json` with the correct structure for 3 templates and 3 option groups. Content is dummy/placeholder — the user will replace prompt text and instructions before shipping.

### Changes Required:

#### 1. Fixture file

**File**: `core/fixtures/onboarding_defaults.json`

**Intent**: Define the shape of the seeded data. Templates carry `name`, `base_prompt`, and `generate_title`. Option groups carry `name` and a list of `options`, each with `name` and `instruction`.

**Contract**: Top-level keys are `"templates"` (list) and `"option_groups"` (list). Each option group has `"name"` and `"options"` (list of `{"name": str, "instruction": str}`). The email template has `"generate_title": true`; the other two have `"generate_title": false`. Three option groups: `"Language"` (English, Polish, German), `"Tone"` (3 options), `"Corporate Buzzword Level"` (3 options). All `base_prompt` and `instruction` values are placeholder strings — the user will edit them.

```json
{
  "templates": [
    {
      "name": "Corporate Email",
      "base_prompt": "TODO: write the corporate email base prompt here.",
      "generate_title": true
    },
    {
      "name": "Teams / IM Message",
      "base_prompt": "TODO: write the Teams/IM message base prompt here.",
      "generate_title": false
    },
    {
      "name": "Peer Feedback",
      "base_prompt": "TODO: write the peer feedback base prompt here.",
      "generate_title": false
    }
  ],
  "option_groups": [
    {
      "name": "Language",
      "options": [
        {"name": "English", "instruction": "TODO: English instruction."},
        {"name": "Polish", "instruction": "TODO: Polish instruction."},
        {"name": "German", "instruction": "TODO: German instruction."}
      ]
    },
    {
      "name": "Tone",
      "options": [
        {"name": "TODO option 1", "instruction": "TODO instruction 1."},
        {"name": "TODO option 2", "instruction": "TODO instruction 2."},
        {"name": "TODO option 3", "instruction": "TODO instruction 3."}
      ]
    },
    {
      "name": "Corporate Buzzword Level",
      "options": [
        {"name": "TODO option 1", "instruction": "TODO instruction 1."},
        {"name": "TODO option 2", "instruction": "TODO instruction 2."},
        {"name": "TODO option 3", "instruction": "TODO instruction 3."}
      ]
    }
  ]
}
```

### Success Criteria:

#### Automated Verification:

- File parses as valid JSON: `python -c "import json; json.load(open('core/fixtures/onboarding_defaults.json'))"`

#### Manual Verification:

- Spot-check that the JSON has 3 templates and 3 option groups with the expected keys

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding.

---

## Phase 3: Signal Handler and Seeding Logic

### Overview

Connect the `user_logged_in` signal in `CoreConfig.ready()`. The handler performs the two-condition skip check, loads the fixture, seeds all data atomically, and creates `OnboardingState` as the last write inside the transaction.

### Changes Required:

#### 1. Signal handler

**File**: `core/apps.py`

**Intent**: Override `ready()` to connect `user_logged_in` to a `seed_onboarding_defaults` handler. The handler: (a) skips if `OnboardingState` exists for the user; (b) skips if the user already has any `Template` or `OptionGroup`; (c) loads the JSON fixture; (d) creates Templates, then OptionGroups + Options, then `OnboardingState` — all inside a single `transaction.atomic()`.

**Contract**: Import `user_logged_in` from `django.contrib.auth.signals`. Import models lazily (inside the handler or at module top after `AppConfig.ready()` — use `django.apps.apps.get_model` or a local import to avoid app registry issues at startup). Fixture path resolved via `Path(__file__).parent / "fixtures" / "onboarding_defaults.json"`.

The `OnboardingState.objects.create(user=user)` call must be the **last** write in the transaction so any earlier DB error leaves the user without an `OnboardingState` row and therefore retryable.

### Success Criteria:

#### Automated Verification:

- `uv run pytest` — all existing tests still pass
- `uv run ruff check .` — no lint errors
- `uv run ruff format .` — no formatting changes

#### Manual Verification:

- Start the dev server: `uv run manage.py runserver`
- Create a fresh test user (or delete the existing user from the DB and recreate)
- Log in — Generate page should show the 3 seeded templates and option group buttons
- Log out and log back in — no duplicate templates or option groups
- Manually delete all templates and option groups via the app UI
- Log out and log back in — Generate page shows the "no templates" message, NOT re-seeded content

**Implementation Note**: After completing this phase and all automated and manual verification passes, pause here before proceeding to tests.

---

## Phase 4: Tests

### Overview

Cover the four meaningful signal-handler paths: first-login seeding, second-login idempotency, pre-existing-content skip, and delete-then-login no-reseed.

### Changes Required:

#### 1. Test file

**File**: `tests/test_onboarding.py`

**Intent**: Test the four scenarios using `user_logged_in.send(sender=user.__class__, request=None, user=user)` to fire the signal directly, without needing a full HTTP login. Use `@pytest.mark.django_db`.

**Contract**: Four test functions — names and scenarios below. Each uses the `user` fixture from `conftest.py`.

- `test_first_login_seeds_defaults`: fire signal once → assert `Template.objects.filter(user=user).count() == 3`, `OptionGroup.objects.filter(user=user).count() == 3`, and `OnboardingState.objects.filter(user=user).exists() is True`
- `test_second_login_does_not_reseed`: fire signal twice → assert counts are still 3 (not 6) and only one `OnboardingState` row exists
- `test_user_with_existing_content_is_not_seeded`: create one `Template` for the user manually, fire signal → assert `Template.objects.filter(user=user).count() == 1` (unchanged), `OnboardingState` does not exist
- `test_deleting_defaults_then_logging_in_does_not_reseed`: fire signal (seeded), delete all user templates and option groups, fire signal again → assert `Template.objects.filter(user=user).count() == 0` and `OptionGroup.objects.filter(user=user).count() == 0` (not re-seeded)

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_onboarding.py -v` — all 4 tests pass
- `uv run pytest` — full suite passes
- `uv run ruff check .`
- `docker build .` — Docker build passes

#### Manual Verification:

- Review that test names and assertions match the four described scenarios exactly

**Implementation Note**: After completing this phase and all automated verification passes, pause here for final manual review.

---

## Testing Strategy

### Unit Tests:

- Signal fires + seeds on first login (counts, OnboardingState created)
- Second login does not reseed (idempotency)
- Pre-existing-content skip (no OnboardingState created)
- Delete-then-login does not reseed (OnboardingState already exists from first seed)

### Integration Tests:

- N/A — the signal path is fully exercised by firing `user_logged_in` directly in tests

### Manual Testing Steps:

1. Start dev server; log in as a new user → confirm Generate page shows seeded templates and option group buttons
2. Log out and back in → confirm no duplicates
3. Delete all templates and option groups via the UI → log out and back in → confirm no re-seeding

## Migration Notes

Existing users (created before this feature ships) who already have templates or option groups will not be seeded — the second condition of the skip check (`Template` or `OptionGroup` exists) covers them. Existing users with zero content will receive the defaults on their next login, which is the intended behaviour.

## References

- Roadmap entry: `context/foundation/roadmap.md` — S-06
- Migration pattern: `core/migrations/0004_dailygenerationcount.py`
- AppConfig.ready() signal connection: Django docs — `user_logged_in` signal

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: OnboardingState Model and Migration

#### Automated

- [x] 1.1 Migration generates cleanly (`uv run manage.py makemigrations --check`) — c6e6073
- [x] 1.2 Migration applies cleanly (`uv run manage.py migrate`) — c6e6073
- [x] 1.3 Existing tests pass (`uv run pytest`) — c6e6073

#### Manual

- [ ] 1.4 OnboardingState visible in Django admin

### Phase 2: Fixture File

#### Automated

- [x] 2.1 JSON parses cleanly (`python -c "import json; json.load(open('core/fixtures/onboarding_defaults.json'))"`)

#### Manual

- [x] 2.2 Spot-check: 3 templates and 3 option groups with correct keys

### Phase 3: Signal Handler and Seeding Logic

#### Automated

- [ ] 3.1 Existing tests pass (`uv run pytest`)
- [ ] 3.2 Lint passes (`uv run ruff check .`)
- [ ] 3.3 Formatting clean (`uv run ruff format .`)

#### Manual

- [ ] 3.4 Fresh login seeds templates and option groups
- [ ] 3.5 Second login produces no duplicates
- [ ] 3.6 Delete-all then log back in does not re-seed

### Phase 4: Tests

#### Automated

- [ ] 4.1 New tests pass (`uv run pytest tests/test_onboarding.py -v`)
- [ ] 4.2 Full suite passes (`uv run pytest`)
- [ ] 4.3 Lint passes (`uv run ruff check .`)
- [ ] 4.4 Docker build passes (`docker build .`)

#### Manual

- [ ] 4.5 Test names and assertions match the four described scenarios
