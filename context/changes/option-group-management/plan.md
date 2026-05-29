# Option Group Management — Implementation Plan

## Overview

Build the CRUD management UI for `OptionGroup` and its child `Option` records, covering FR-004/005/006 from the PRD. Data models and migrations already exist; this change adds a `unique_together` constraint, four CBVs with an InlineFormSet, three templates, nav integration, and a full test suite.

## Current State Analysis

The `OptionGroup` (user-owned, name) and `Option` (group-owned, name + instruction) models are fully defined in `core/models.py` and migrated. `Option` has no `Meta` class at all today — no ordering, no uniqueness constraint. Admin interfaces are registered. Model-level tests (creation, cascade deletion) already pass.

Template management is the direct prior art: four CBVs (List/Create/Update/Delete), user-scoped querysets, `LoginRequiredMixin`, `form.as_p` templates extending `base.html`, and a seven-test pytest suite. The pattern is replicated verbatim except for the nested Options.

Nothing in `core/views.py`, `core/urls.py`, or the templates directory covers option groups yet.

## Desired End State

A logged-in user can navigate to `/option-groups/`, see their groups listed with option counts, create a new group with at least one option inline, edit or delete existing groups, and see a cascade warning on the delete confirmation page. Option names within a group must be unique; duplicate names are rejected with a form error. The "Option Groups" link appears in the navbar alongside "Templates".

### Key Discoveries:

- `Option.Meta` is absent — `unique_together` and ordering can be added without touching any existing migration data
- `core/urls.py` is included at `path("templates/", ...)` — option group routes need a separate include at `path("option-groups/", ...)`; a new `core/option_group_urls.py` avoids restructuring the existing template URL file
- `base.html:13` — the Templates nav link is a bare `<a>` tag; the Option Groups link slots in identically
- `inlineformset_factory` with a custom `BaseInlineFormSet` subclass is the correct Django primitive for the parent+children form; the `empty_form` attribute provides the JavaScript clone source

## What We're NOT Doing

- Wiring option groups into the text transformation workflow (FR-008) — separate change
- Ordering control within a group — options are alpha-ordered (Django default queryset order)
- Bulk import/export — out of scope per PRD Non-Goals
- Option-level standalone CRUD routes — all option management happens inline on the group form

## Implementation Approach

Mirror template-management in structure: new URL file → new views in `core/views.py` → new templates. The only structural addition is `core/forms.py` (new file) for the custom `BaseInlineFormSet` and the `inlineformset_factory` call, keeping views clean. JavaScript in the form template handles dynamic add/remove rows using `formset.empty_form` as the clone source.

## Critical Implementation Details

**Formset POST data format** — tests must include management form keys or Django silently rejects the POST as a GET. For a create POST with one option the data dict must contain: `options-TOTAL_FORMS`, `options-INITIAL_FORMS` (0 for create), `options-MIN_NUM_FORMS`, `options-MAX_NUM_FORMS`, and per-row keys `options-N-name`, `options-N-instruction`, `options-N-DELETE`. For update POSTs, each existing option row must also include `options-N-id` set to the option's pk and `options-INITIAL_FORMS` must equal the number of existing options.

**`form_valid` orchestration — CreateView** — `OptionGroupCreateView.form_valid` must NOT call `super().form_valid()` (which would save and redirect immediately). Instead: assign `form.instance.user`, save the group form to get `self.object`, bind the formset to `self.object`, validate and save the formset, then redirect. If the formset is invalid after the main form passes, the group save must be rolled back — wrap the entire save sequence in `transaction.atomic()`.

**`form_valid` orchestration — UpdateView** — `OptionGroupUpdateView.form_valid` must also NOT call `super().form_valid()`. `self.object` already exists (no save needed to obtain a PK), so bind the formset immediately with `OptionFormSet(request.POST, instance=self.object)`. Validate and save both the group form and the formset inside `transaction.atomic()` so that a formset validation failure after a successful `form.save()` is rolled back. Return `render_to_response(context)` with the invalid formset if validation fails.

---

## Phase 1: Data Model, Views, and URLs

### Overview

Add `unique_together` to `Option`, create the migration, implement four OptionGroup CBVs with inline formset validation, and wire the URL routes.

### Changes Required:

#### 1. Option model

**File**: `core/models.py`

**Intent**: Add a `Meta` inner class to `Option` so that (group, name) pairs are unique at the database level.

**Contract**: `Option.Meta.unique_together = [("group", "name")]`. This produces a `UNIQUE` constraint on `(group_id, name)` in the migration. No `ordering` is added — options render in insertion order, which is acceptable for the MVP.

#### 2. Migration

**File**: `core/migrations/0002_option_unique_together.py` (generated name may differ)

**Intent**: Generate and apply the migration for the new `unique_together` constraint.

**Contract**: Run `uv run manage.py makemigrations core` then `uv run manage.py migrate`. The migration must apply cleanly against the dev SQLite database (any existing options with duplicate names in the same group would need manual cleanup first — not a concern for a fresh dev DB).

#### 3. Custom InlineFormSet

**File**: `core/forms.py` (new file)

**Intent**: Define `RequiredOptionInlineFormSet` (a `BaseInlineFormSet` subclass) that enforces two business rules, and define `OptionFormSet` using `inlineformset_factory`.

**Contract**: `RequiredOptionInlineFormSet.clean()` raises `ValidationError` when (a) all non-deleted forms total fewer than 1, or (b) any two non-deleted forms share the same `name` value (case-sensitive). `OptionFormSet = inlineformset_factory(OptionGroup, Option, formset=RequiredOptionInlineFormSet, fields=["name", "instruction"], extra=1, can_delete=True)`.

#### 4. OptionGroup views

**File**: `core/views.py`

**Intent**: Add `OptionGroupListView`, `OptionGroupCreateView`, `OptionGroupUpdateView`, and `OptionGroupDeleteView` following the same `LoginRequiredMixin` + user-scoped queryset pattern as the template views. Create and Update must handle `OptionFormSet` alongside the group form.

**Contract**:
- `OptionGroupListView`: `ListView`, `get_queryset` filters `OptionGroup.objects.filter(user=self.request.user)`
- `OptionGroupCreateView`: `CreateView`, `fields = ["name"]`, `success_url = reverse_lazy("option-group-list")`. Override `get_context_data` to attach `OptionFormSet(self.request.POST or None)` as `"formset"`. Override `form_valid` to: assign user, save group into `self.object`, bind formset to instance, validate formset — if valid save and redirect, if invalid return `render_to_response(context)` without saving the group (no partial saves).
- `OptionGroupUpdateView`: same as Create but `get_queryset` filters by user (404 on other users' groups), and `get_context_data` passes `instance=self.object` to `OptionFormSet`.
- `OptionGroupDeleteView`: `DeleteView`, `get_queryset` filters by user, `success_url = reverse_lazy("option-group-list")`.

#### 5. Option group URL module

**File**: `core/option_group_urls.py` (new file)

**Intent**: Define the four URL patterns for OptionGroup CRUD, mirroring `core/urls.py` in structure.

**Contract**: Four `path()` entries with names `option-group-list`, `option-group-create`, `option-group-update`, `option-group-delete`.

#### 6. Root URL include

**File**: `korpotron/urls.py`

**Intent**: Mount the new URL module at the `/option-groups/` prefix.

**Contract**: Add `path("option-groups/", include("core.option_group_urls"))` to `urlpatterns`.

### Success Criteria:

#### Automated Verification:

- Migration applies cleanly: `uv run manage.py migrate`
- No import errors: `uv run manage.py check`
- All existing tests still pass: `uv run pytest`
- Linting passes: `uv run ruff check .`

#### Manual Verification:

- `/option-groups/` returns 302 to login when unauthenticated
- Authenticated user can navigate to `/option-groups/` without a 500
- `/option-groups/new/` and `/option-groups/1/edit/` render without a template-not-found 500 (Django will show the standard "template missing" error, which confirms the view is wired correctly)

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding to Phase 2.

---

## Phase 2: HTML Templates and Nav

### Overview

Create the three OptionGroup templates and update the navbar. The form template includes JavaScript for dynamic add/remove of option rows.

### Changes Required:

#### 1. Option group list template

**File**: `templates/core/option_group_list.html` (new file)

**Intent**: Render the user's option groups in a table with a count of options per group and Edit/Delete action links. Show an empty-state message and a "New option group" button in the header, mirroring `template_list.html`.

**Contract**: Extends `base.html`. Iterates `object_list`. Shows `{{ group.options.count }}` options column. Uses `{% url 'option-group-create' %}`, `{% url 'option-group-update' group.pk %}`, `{% url 'option-group-delete' group.pk %}`.

#### 2. Option group form template

**File**: `templates/core/option_group_form.html` (new file)

**Intent**: Render a single form page for both create and edit, showing the group name field and an inline section for its options. Each option row has name + instruction fields and a Delete checkbox. An "Add option" button appends a new row using JavaScript.

**Contract**: Extends `base.html`. Dynamic heading ("New option group" vs "Edit option group") using `{% if object %}`. Renders `{{ form.as_p }}` for the group name. Renders `{{ formset.management_form }}` and then each `{{ option_form }}` row in a loop. Includes a `<template id="empty-option-row">` element containing `{{ formset.empty_form }}` rendered as a row. JavaScript reads `id_options-TOTAL_FORMS`, clones the `<template>`, replaces all `__prefix__` occurrences with the current count, appends to the formset container, and increments the management form count. Save and Cancel buttons at the bottom.

#### 3. Option group delete confirmation template

**File**: `templates/core/option_group_confirm_delete.html` (new file)

**Intent**: Ask for deletion confirmation, prominently showing the group name and the count of options that will be cascade-deleted.

**Contract**: Extends `base.html`. Message: `Delete "{{ object.name }}"? This will also permanently delete its {{ object.options.count }} option{{ object.options.count|pluralize }}.` POST form with "Delete" and "Cancel" buttons, mirroring `template_confirm_delete.html`.

#### 4. Navbar link

**File**: `templates/base.html`

**Intent**: Add an "Option Groups" link to the authenticated-user nav, alongside the existing "Templates" link.

**Contract**: Insert `<a class="nav-link text-white" href="{% url 'option-group-list' %}">Option Groups</a>` immediately after the existing Templates `<a>` tag on line 13.

### Success Criteria:

#### Automated Verification:

- All tests still pass: `uv run pytest`
- Linting passes: `uv run ruff check .`

#### Manual Verification:

- "Option Groups" nav link appears in the navbar when logged in
- List page at `/option-groups/` renders correctly (empty state and populated state)
- Create form at `/option-groups/new/` renders with one empty option row; "Add option" button appends a new row
- Edit form pre-populates group name and existing options
- Deleting a group with 2 options shows "This will also permanently delete its 2 options"
- Submitting create form with no options shows a validation error; form does not save
- Submitting create form with two options sharing the same name shows a validation error

**Implementation Note**: After completing this phase and manual testing passes, pause before proceeding to Phase 3.

---

## Phase 3: Tests

### Overview

Create a pytest test file for OptionGroup views, mirroring `test_template_views.py` in structure and adding formset-specific cases.

### Changes Required:

#### 1. Option group view tests

**File**: `tests/test_option_group_views.py` (new file)

**Intent**: Cover authentication guards, user-isolation security, happy-path CRUD, and the two formset business rules (minimum one option, unique names within group).

**Contract**: Fixtures: `user` (from conftest), `other_user`, `option_group` (belonging to `user`, with one `Option`), `other_option_group` (belonging to `other_user`). Helper: a `formset_data(name, options)` dict builder that assembles the management form keys and per-row keys — reduces boilerplate across tests. Nine test functions:

1. `test_option_group_list_requires_login` — GET `/option-groups/` unauthenticated → 302
2. `test_option_group_list_shows_only_own` — logged-in user sees their group but not `other_option_group`
3. `test_option_group_create` — valid POST → 302 to list; group + options created with correct `user`
4. `test_option_group_update` — valid POST → 302 to list; name and option instruction updated via `refresh_from_db()`
5. `test_option_group_delete` — POST to delete → 302 to list; group and its options removed
6. `test_option_group_update_other_user_returns_404` — logged-in user POSTs to other user's group edit → 404
7. `test_option_group_delete_other_user_returns_404` — same for delete
8. `test_option_group_create_requires_at_least_one_option` — POST with all option rows marked DELETE (or TOTAL_FORMS=0) → 200, formset error, no group saved
9. `test_option_group_create_rejects_duplicate_option_names` — POST with two options sharing the same name → 200, formset error, no group saved

### Success Criteria:

#### Automated Verification:

- All 9 new view tests pass: `uv run pytest tests/test_option_group_views.py`
- Full test suite passes: `uv run pytest`
- Linting passes: `uv run ruff check .`
- Docker build succeeds: `docker build .`

---

## Testing Strategy

### Unit Tests:

- `RequiredOptionInlineFormSet.clean()` is covered indirectly by view tests 8 and 9; no separate unit test needed given the simple logic

### Integration Tests:

- Nine view tests in `test_option_group_views.py` as specified above

### Manual Testing Steps:

1. Log in, confirm "Option Groups" link is visible in nav
2. Navigate to `/option-groups/` — confirm empty state with "New option group" button
3. Create a group named "Tone" with two options ("Formal" / "Casual") — confirm appears in list with "2" count
4. Click Edit — confirm form pre-populates; change one option's instruction and save; confirm change persists
5. Try to save an edit with both options having the same name — confirm error shown, no save
6. Try to save an edit with all options deleted — confirm "at least one option" error
7. Delete the group — confirm cascade warning shows "2 options"; confirm redirect to empty list

## Migration Notes

The `unique_together` constraint applies only going forward. A fresh dev database has no conflicting data. If the dev database has existing duplicate-named options in the same group (unlikely), they must be cleaned up manually before migrating.

## References

- Prior art: `core/views.py` (template views pattern)
- Prior art: `tests/test_template_views.py` (test structure to mirror)
- Models: `core/models.py:37-47` (Option model to update)
- Base template: `templates/base.html:13` (nav insertion point)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Data Model, Views, and URLs

#### Automated

- [x] 1.1 Migration applies cleanly: `uv run manage.py migrate` — 2071b2b
- [x] 1.2 No import errors: `uv run manage.py check` — 2071b2b
- [x] 1.3 All existing tests still pass: `uv run pytest` — 2071b2b
- [x] 1.4 Linting passes: `uv run ruff check .` — 2071b2b

#### Manual

- [x] 1.5 `/option-groups/` returns 302 to login when unauthenticated — 2071b2b
- [x] 1.6 Authenticated user can navigate to `/option-groups/` without a 500 — 2071b2b
- [x] 1.7 `/option-groups/new/` and `/option-groups/1/edit/` render without a template-not-found 500 — 2071b2b

### Phase 2: HTML Templates and Nav

#### Automated

- [x] 2.1 All tests still pass: `uv run pytest`
- [x] 2.2 Linting passes: `uv run ruff check .`

#### Manual

- [x] 2.3 "Option Groups" nav link appears in the navbar when logged in
- [x] 2.4 List page renders correctly (empty state and populated state)
- [x] 2.5 Create form renders with one empty option row; "Add option" button appends a new row
- [x] 2.6 Edit form pre-populates group name and existing options
- [x] 2.7 Delete confirmation shows option count
- [x] 2.8 Submitting create with no options shows a validation error
- [x] 2.9 Submitting create with duplicate option names shows a validation error

### Phase 3: Tests

#### Automated

- [ ] 3.1 All 9 new view tests pass: `uv run pytest tests/test_option_group_views.py`
- [ ] 3.2 Full test suite passes: `uv run pytest`
- [ ] 3.3 Linting passes: `uv run ruff check .`
- [ ] 3.4 Docker build succeeds: `docker build .`
