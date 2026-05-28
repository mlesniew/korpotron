# Core Data Model Implementation Plan

## Overview

Create a `core` Django app containing three ORM models — `Template`, `OptionGroup`, and `Option` — each with user ownership and appropriate FK relationships. Ship with an initial migration and Django admin registrations so all three tables exist in the database and are browsable.

## Current State Analysis

The project has no custom Django apps. `INSTALLED_APPS` contains only built-in Django apps (`settings.py:34-41`). No custom models or migrations exist beyond Django's own. The `korpotron/` directory functions purely as the project configuration package (settings, URL routing, WSGI entry point).

## Desired End State

A `core` app is registered in `INSTALLED_APPS`. Three models exist with migrations applied:
- `Template`: owned by a `User`, with `name`, `base_prompt`, and `generate_title` fields
- `OptionGroup`: owned by a `User`, with a `name` field
- `Option`: belonging to an `OptionGroup`, with `name` and `instruction` fields

All three are browsable in Django admin. Pytest tests cover model creation, `__str__`, and FK cascade deletion. Docker build succeeds after the change.

### Key Discoveries

- `settings.py:34-41` — `INSTALLED_APPS` has no custom apps; `core` will be the first
- `pyproject.toml` — `DJANGO_SETTINGS_MODULE` already configured for pytest; no extra test setup needed
- PRD Business Logic — one option per group at a time is enforced by the UI (radio buttons), not a DB constraint; no `unique_together` needed on `Option`
- `is_response` field — deferred to v2 per user decision; excluded from this plan

## What We're NOT Doing

- `is_response` flag on Template — deferred to v2
- Option ordering field — pk order is sufficient for MVP
- Template–OptionGroup association — the generation flow (S-03) assembles prompts from the user's option groups; no explicit link is needed in the data model
- Any views, forms, URL routing, or templates — that's S-01 and S-02

## Implementation Approach

Create the `core` app directory, define all three models in `models.py`, register them in `admin.py`, add `"core"` to `INSTALLED_APPS`, then generate and apply the initial migration. Tests follow as a separate phase.

## Phase 1: Core app — models, admin, migration

### Overview

Scaffold the `core` Django app, write all three models, register in admin, update settings, and generate and apply the migration. After this phase `uv run manage.py check` passes, the three tables exist in the database, and the admin shows all three models with useful column displays.

### Changes Required

#### 1. Core app package marker

**File**: `core/__init__.py` (new, empty)

**Intent**: Mark `core/` as a Python package. Required for Django to discover the app.

**Contract**: Empty file.

---

#### 2. App config

**File**: `core/apps.py` (new)

**Intent**: Declare the Django app config so `INSTALLED_APPS` can reference `"core"` cleanly.

**Contract**: `CoreConfig(AppConfig)` with `name = "core"`. No `default_auto_field` override — `settings.py` already sets `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` project-wide.

---

#### 3. Models

**File**: `core/models.py` (new)

**Intent**: Define `Template`, `OptionGroup`, and `Option` with the fields from the PRD and user ownership via FK.

**Contract**:
- `Template`: `user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="templates")`, `name = CharField(max_length=200)`, `base_prompt = TextField()`, `generate_title = BooleanField(default=False)`. `Meta.ordering = ["name"]`. `__str__` returns `self.name`.
- `OptionGroup`: `user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="option_groups")`, `name = CharField(max_length=200)`. `Meta.ordering = ["name"]`. `__str__` returns `self.name`.
- `Option`: `group = ForeignKey(OptionGroup, on_delete=CASCADE, related_name="options")`, `name = CharField(max_length=200)`, `instruction = TextField()`. `__str__` returns `self.name`.

Use `settings.AUTH_USER_MODEL` (the string constant from `django.conf`) for the FK rather than importing `User` directly — the standard Django convention for FK references to the user model.

---

#### 4. Admin registrations

**File**: `core/admin.py` (new)

**Intent**: Register all three models in the Django admin with useful column displays for development inspection.

**Contract**:
- `TemplateAdmin(ModelAdmin)`: `list_display = ["name", "user", "generate_title"]`
- `OptionGroupAdmin(ModelAdmin)`: `list_display = ["name", "user"]`
- `OptionAdmin(ModelAdmin)`: `list_display = ["name", "group"]`

Use `@admin.register(Model)` decorator form (matches Django convention; keeps registrations co-located with their config).

---

#### 5. Register app in settings

**File**: `korpotron/settings.py`

**Intent**: Tell Django the `core` app exists so it discovers models, migrations, and admin registrations.

**Contract**: Append `"core"` to `INSTALLED_APPS` after the built-in apps block (`settings.py:41`).

---

#### 6. Initial migration

**File**: `core/migrations/0001_initial.py` (generated)

**Intent**: Create the three database tables.

**Contract**: Generate via `uv run manage.py makemigrations core`, then apply with `uv run manage.py migrate`. Commit the generated file alongside the app code.

### Success Criteria

#### Automated Verification

- Django system check passes: `uv run manage.py check`
- No unapplied migrations after applying: `uv run manage.py makemigrations --check`
- Migration applies cleanly: `uv run manage.py migrate`
- Ruff lint passes: `uv run ruff check .`
- Existing test suite still passes: `uv run pytest`

#### Manual Verification

- `/admin/` shows a `Core` section with `Templates`, `Option groups`, and `Options`
- Can create a `Template`, `OptionGroup`, and `Option` record via admin without errors
- `list_display` columns (name, user/group, generate_title) visible in each admin list view

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to Phase 2.

---

## Phase 2: Tests

### Overview

Write pytest tests covering model creation, `__str__` representations, and FK cascade deletion. After this phase, all new tests pass alongside the existing auth tests, and the Docker build succeeds.

### Changes Required

#### 1. Shared test fixtures

**File**: `tests/conftest.py` (new)

**Intent**: Provide a shared `user` fixture available to all test modules, consolidating the duplicate that currently lives in `test_auth.py`.

**Contract**: `user` fixture with `db: None` parameter — `User.objects.create_user(username="testuser", password="pw")`.

---

#### 2. Remove local `user` fixture from auth tests

**File**: `tests/test_auth.py` (modify)

**Intent**: Remove the module-local `user` fixture (lines 6–8) so all test modules draw from `conftest.py` instead.

**Contract**: Delete the `user` fixture function. Auth tests continue to work unchanged; pytest picks up the fixture from `conftest.py` automatically.

---

#### 3. Model tests

**File**: `tests/test_core_models.py` (new)

**Intent**: Verify that each model stores and returns correct field values, that `__str__` returns the name, and that FK cascades work as expected.

**Contract**:
- Uses `user` from `conftest.py` — no local fixture definition
- `test_template_creation` — create `Template`, assert field values, `str(t) == t.name`
- `test_option_group_creation` — create `OptionGroup`, assert fields, `str(og) == og.name`
- `test_option_creation` — create `Option` inside a group, assert fields, `str(o) == o.name`
- `test_user_delete_cascades_templates` — delete the user, assert `Template.objects.count() == 0`
- `test_user_delete_cascades_option_groups` — delete the user, assert `OptionGroup.objects.count() == 0`
- `test_option_group_delete_cascades_options` — delete the group, assert `Option.objects.count() == 0`

### Success Criteria

#### Automated Verification

- New model tests pass: `uv run pytest tests/test_core_models.py`
- Full test suite passes: `uv run pytest`
- Ruff lint passes: `uv run ruff check .`
- Docker build succeeds: `docker build .`

#### Manual Verification

- No regressions in existing auth tests (covered by the full suite run above)

---

## Testing Strategy

### Unit Tests

- Field defaults (`generate_title=False`)
- `__str__` for all three models
- User → Template cascade delete
- User → OptionGroup cascade delete
- OptionGroup → Option cascade delete

### Manual Testing Steps

1. Run dev server: `uv run manage.py runserver`
2. Visit `/admin/`, log in as a superuser (`uv run manage.py createsuperuser`)
3. Create a `Template` with a name, base prompt, and `generate_title` checked — confirm it saves and appears in the list with the correct columns
4. Create an `OptionGroup` with a name — confirm it saves and shows the owner
5. Create an `Option` under that group — confirm it saves and shows the group name in `list_display`

## Migration Notes

This is the first custom migration. It creates three new tables; no existing data is affected. To roll back: `uv run manage.py migrate core zero` drops all three tables.

## References

- PRD: `context/foundation/prd.md` — FR-001 (Template fields), FR-004 (OptionGroup + Option structure)
- Roadmap: `context/foundation/roadmap.md` — F-02 (this slice)
- Auth scaffold plan: `context/changes/auth-scaffold/plan.md` (pattern reference)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Core app — models, admin, migration

#### Automated

- [ ] 1.1 Django system check passes: `uv run manage.py check`
- [ ] 1.2 No unapplied migrations: `uv run manage.py makemigrations --check`
- [ ] 1.3 Migration applies cleanly: `uv run manage.py migrate`
- [ ] 1.4 Ruff lint passes: `uv run ruff check .`
- [ ] 1.5 Existing test suite still passes: `uv run pytest`

#### Manual

- [ ] 1.6 `/admin/` shows Core section with all three models
- [ ] 1.7 Can create Template, OptionGroup, and Option via admin without errors
- [ ] 1.8 `list_display` columns visible in each admin list view

### Phase 2: Tests

#### Automated

- [ ] 2.1 New model tests pass: `uv run pytest tests/test_core_models.py`
- [ ] 2.2 Full test suite passes: `uv run pytest`
- [ ] 2.3 Ruff lint passes: `uv run ruff check .`
- [ ] 2.4 Docker build succeeds: `docker build .`

#### Manual

- [ ] 2.5 No regressions in existing auth tests
