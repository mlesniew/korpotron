# Option Group Edit UX — Implementation Plan

## Overview

Rebuild the option-group editing experience from a Django formset page-reload flow to a fully REST-driven UI. Every option operation — list, create, update, delete — goes through a dedicated JSON endpoint. The edit page is a static shell: no server-side option rendering. The group name rename is also AJAX. No "Save all" button; each action takes effect immediately.

## Current State Analysis

The current edit flow is formset-based: the user edits all options on one page and submits a single POST. Specific problems:

- `optiongroup_form.html:18-26` — each option row renders with `{{ option_form.as_p }}`, producing unstyled paragraphs and an exposed `DELETE` checkbox (the Django formset delete mechanic)
- `views.py:96-120` — `OptionGroupUpdateView` wires a formset, saves atomically; tightly coupled to the form submission model
- `forms.py:10-32` — `RequiredOptionInlineFormSet` enforces at least one option, blocking empty groups

The generate page (`views.py:131-143`) currently passes all groups including empty ones (no filtering).

### Key Discoveries

- `core/models.py:32` — `unique_together = [("user", "name")]` on `OptionGroup`; rename must check uniqueness before saving
- `core/models.py:47-48` — `unique_together = [("group", "name")]` on `Option`; create/update must enforce uniqueness within the group in the view
- `views.py:7` — `Count` already imported from `django.db.models`; available for the `HomeView` empty-group filter
- `views.py:146-238` — `generate_api` shows the established pattern for JSON function views: `json.loads(request.body)`, `@login_required` + `@require_POST`, `JsonResponse` returns

## Desired End State

**REST endpoints** (five in total):
- `GET  /option-groups/<pk>/options/` — list options for a group (JSON array)
- `POST /option-groups/<pk>/options/` — create a new option
- `POST /option-groups/<pk>/options/<id>/update/` — update name/instruction
- `POST /option-groups/<pk>/options/<id>/delete/` — delete an option
- `POST /option-groups/<pk>/rename/` — rename the group

**Edit page** (`GET /option-groups/<pk>/edit/`) — renders a static shell only: group name, an empty `#option-rows` container, an "Add option" button, a warning placeholder. No option data in the HTML. On `DOMContentLoaded`, JS fetches the list endpoint and renders rows dynamically.

**Create page** — unchanged pattern: simple Django form POST (group name only). On success, redirects to the edit page for the new group.

**Generate page** (`HomeView`) — excludes option groups with zero options, server-side.

### Key Discoveries

- No model changes required
- `OptionFormSet` and `RequiredOptionInlineFormSet` will be deleted entirely
- `OptionGroupUpdateView` becomes a `DetailView` with no `prefetch_related` (options are fetched client-side, not in the server render)
- `OptionGroupCreateView` loses formset handling; redirects to edit page after save
- Five new function views follow the `generate_api` pattern

## What We're NOT Doing

- No inline reorder / drag-and-drop of options
- No bulk-edit of multiple options in one request
- No visual distinction between new and saved rows
- No Playwright/Selenium tests for client-side JS behaviour
- No changes to `OptionGroupDeleteView` (group-level delete stays as a confirm-form page)
- No changes to `OptionGroupListView`

## Implementation Approach

Three sequential phases:

1. **Backend**: strip formset from create/update views, add five REST endpoints, update `HomeView`
2. **Template**: rebuild `optiongroup_form.html` as a static shell + vanilla JS that fetches options on load and manages all mutations
3. **Tests**: remove obsolete formset tests, add endpoint tests for all five new surfaces

All mutation endpoints (`rename`, `create`, `update`, `delete`) are function views with `@login_required` + `@require_POST`. The list endpoint uses `@login_required` only (GET). All return `JsonResponse`. Ownership is enforced via `get_object_or_404` with user filter. Uniqueness errors use pre-save queryset checks, not `IntegrityError` handling.

## Critical Implementation Details

**Ownership enforcement pattern** — each endpoint resolves the `OptionGroup` first with `get_object_or_404(OptionGroup, pk=group_pk, user=request.user)`, then the `Option` (where applicable) with `get_object_or_404(Option, pk=pk, group=group)`. Wrong-user requests get 404 on the group lookup, consistent with the rest of the app.

**Uniqueness checks** — use pre-save queryset checks (`.filter(...).exists()`) rather than catching `IntegrityError`. The `unique_together` constraints exist at the DB level, but catching `IntegrityError` makes error messages fragile.

**CSRF token for AJAX** — the edit page is a `DetailView` with no `<form>` element. Read the CSRF token from the `csrftoken` cookie Django's middleware sets (standard Django AJAX pattern). Pass as `X-CSRFToken` header in all mutation `fetch()` calls.

**Initial empty-warning state** — because options are not in the HTML at page load, the warning's initial visibility is unknown until the first fetch completes. Start the warning hidden (`d-none`); call `updateEmptyWarning()` after the initial list fetch renders rows.

**Row save-button state** — the Save button on each row starts `disabled`. A single delegated `input` listener on `#option-rows` handles all rows (existing + newly added): `e.target.closest('[data-option-row]')`.

---

## Phase 1: Backend — REST endpoints + simplified views

### Overview

Remove formset coupling from the create and update views, add five new JSON views, update `HomeView` to filter empty groups.

### Changes Required

#### 1. `core/forms.py` — remove formset, add `OptionForm`

**File**: `core/forms.py`

**Intent**: Delete `RequiredOptionInlineFormSet` and `OptionFormSet` entirely — no longer used. Add a simple `OptionForm` ModelForm for validating option create/update payloads in the new endpoints.

**Contract**: `OptionForm` is a `ModelForm` for `Option` with `fields = ["name", "instruction"]`. No custom clean methods — uniqueness within the group is checked in the view before saving.

#### 2. `core/views.py` — simplify `OptionGroupCreateView`

**File**: `core/views.py`

**Intent**: Strip all formset handling. After creating the group, redirect to its edit page so the user can add options via AJAX.

**Contract**: Remove `get_context_data` and the formset branch in `form_valid`. Keep `form.instance.user = self.request.user`. Replace `success_url = reverse_lazy("option-group-list")` with a `get_success_url()` method returning `reverse("option-group-update", kwargs={"pk": self.object.pk})`.

#### 3. `core/views.py` — convert `OptionGroupUpdateView` to `DetailView`

**File**: `core/views.py`

**Intent**: The edit URL now only serves a GET (renders the static shell); all mutations go to dedicated endpoints. A POST to the edit URL returns 405.

**Contract**: Change base class to `DetailView`. Remove `fields`, `success_url`, `get_context_data`, `form_valid`. Set `template_name = "core/optiongroup_form.html"`. Override `get_queryset` to filter by user — no `prefetch_related` needed (options are not rendered server-side). Add `DetailView` to the `django.views.generic` import block.

#### 4. `core/views.py` — update `HomeView` to filter empty groups

**File**: `core/views.py`

**Intent**: Exclude option groups with no options from the generate page.

**Contract**: In `HomeView.get`, annotate the `option_groups` queryset with `options_count=Count("options")` and add `.filter(options_count__gt=0)` before `.prefetch_related("options")`. `Count` is already imported.

#### 5. `core/views.py` — add `option_list`

**File**: `core/views.py`

**Intent**: GET endpoint that returns all options for a group as a JSON array. This is the only read endpoint added; the edit page fetches it on load to populate its rows.

**Contract**:
```python
@login_required
def option_list(request: HttpRequest, group_pk: int) -> JsonResponse:
```
Resolve group with ownership check (`get_object_or_404`). Return `JsonResponse({"options": [{"id": o.pk, "name": o.name, "instruction": o.instruction} for o in group.options.all()]})`. No `@require_POST` — only GET is valid; other methods return Django's default 405.

#### 6. `core/views.py` — add `option_group_rename`

**File**: `core/views.py`

**Intent**: AJAX endpoint to rename an option group. Validates non-empty and unique-for-user before saving.

**Contract**:
```python
@login_required
@require_POST
def option_group_rename(request: HttpRequest, pk: int) -> JsonResponse:
```
Parse JSON body; extract `name`; return `{"error": "..."}` (status 400) if blank; return `{"error": "..."}` (status 400) if `OptionGroup.objects.filter(user=request.user, name=new_name).exclude(pk=group.pk).exists()`; save and return `{"renamed": True}`.

#### 7. `core/views.py` — add `option_create`

**File**: `core/views.py`

**Intent**: Create a new option in an existing group. Returns the created option's `id`, `name`, and `instruction` so JS can assign `data-option-id` to the row.

**Contract**:
```python
@login_required
@require_POST
def option_create(request: HttpRequest, group_pk: int) -> JsonResponse:
```
Parse JSON body; validate with `OptionForm(data=payload)`; check `group.options.filter(name=...).exists()` for duplicates; create option; return `{"id": option.pk, "name": ..., "instruction": ...}`. On failure return `{"errors": form.errors}` (status 400).

#### 8. `core/views.py` — add `option_update`

**File**: `core/views.py`

**Intent**: Update an existing option's name and/or instruction.

**Contract**:
```python
@login_required
@require_POST
def option_update(request: HttpRequest, group_pk: int, pk: int) -> JsonResponse:
```
Parse JSON body; validate with `OptionForm(data=payload, instance=option)`; check `group.options.filter(name=...).exclude(pk=pk).exists()` for duplicates; save; return `{"updated": True}`. On failure return `{"errors": form.errors}` (status 400).

#### 9. `core/views.py` — add `option_delete`

**File**: `core/views.py`

**Intent**: Delete a single option. Allows deletion of the last option — empty groups are permitted.

**Contract**:
```python
@login_required
@require_POST
def option_delete(request: HttpRequest, group_pk: int, pk: int) -> JsonResponse:
```
Resolve group (ownership check), resolve option (membership check), delete, return `{"deleted": True}`.

#### 10. `core/urls.py` — add five new URL patterns

**File**: `core/urls.py`

**Intent**: Expose all five new views. The options URL doubles as list (GET) and create (POST) — same URL, method-dispatched in the view.

**Contract**: Add these paths and import the five new views:
- `option-groups/<int:pk>/rename/` → `option_group_rename`, name `"option-group-rename"`
- `option-groups/<int:group_pk>/options/` → `option_list` for GET, `option_create` for POST — implement as a single dispatcher view, or add two separate named URLs pointing to separate views (use two entries if cleaner: `option-group-options` for list, `option-create` for create)
- `option-groups/<int:group_pk>/options/<int:pk>/update/` → `option_update`, name `"option-update"`
- `option-groups/<int:group_pk>/options/<int:pk>/delete/` → `option_delete`, name `"option-delete"`

For the list/create URL, the simplest approach is a single dispatcher function view at `option-groups/<int:group_pk>/options/` that routes on `request.method` (`GET` → list logic, `POST` → create logic) with a single URL name `"option-list-create"`. This avoids having two URL patterns for the same path.

### Success Criteria

#### Automated Verification

- Tests pass: `uv run pytest tests/test_option_group_views.py`
- Lint passes: `uv run ruff check core/`

#### Manual Verification

- `GET /option-groups/<pk>/edit/` returns 200 (empty shell — no option rows in HTML)
- `POST /option-groups/<pk>/edit/` returns 405
- Creating a group via `/option-groups/new/` redirects to its edit page
- `GET /option-groups/<pk>/options/` returns `{"options": [...]}` with correct data
- All mutation endpoints return expected JSON

---

## Phase 2: Template redesign

### Overview

Rewrite `optiongroup_form.html` as a dual-mode template: create mode (no `object`) is a standard Django form POST; edit mode (`object` present) is a static shell whose option rows are populated entirely by JS after a `fetch` on page load.

### Changes Required

#### 11. `templates/core/optiongroup_form.html` — full redesign

**File**: `templates/core/optiongroup_form.html`

**Intent**: Replace the formset-based template. Create mode renders a simple name form. Edit mode renders a static page shell with no option data; all option content is fetched and rendered by JS.

**Contract**:

Two top-level branches on `{% if not object %}` / `{% else %}`.

**Create mode** (`{% if not object %}`): a standard `<form method="post">` with `{% csrf_token %}`, Bootstrap-styled name field (`form-control`), submit button, Cancel link to list. Same shape as `template_form.html`.

**Edit mode** (`{% else %}`): no `<form>` element. Static HTML structure only:

1. **Group name section** — `<input class="form-control" id="group-name-input" value="{{ object.name }}">`, a "Save" button (`id="group-name-save"`, disabled initially), an error `<span>` (`id="group-name-error"`).

2. **Empty-group warning** — `<div id="empty-warning" class="alert alert-warning d-none">` — starts hidden; JS shows/hides it after rendering options.

3. **Option list container** — `<div id="option-rows"></div>` — empty in the HTML. JS populates this after fetching the list endpoint.

4. **"Add option" button** — `<button id="add-option">` below `#option-rows`.

5. **Back link** — `<a href="{% url 'option-group-list' %}">Back to option groups</a>`.

6. **`<script>` block** — vanilla JS:
   - `getCsrfToken()` — parses the `csrftoken` cookie
   - `buildRow(option)` — creates a `[data-option-row]` div from a `{id, name, instruction}` object (or `null` for a new unsaved row); sets `data-option-id` only when `id` is present. Row structure: Name label + input (`.option-name`), error div (`.option-name-error`), Instruction label + textarea (`.option-instruction`), error div (`.option-instruction-error`), disabled Save button (`.option-save`), Remove button (`.option-remove`)
   - `attachRowListeners(row)` — wires `input` events to enable Save; wires Save click (update or create based on `data-option-id`); wires Remove click (delete or DOM-remove)
   - `updateEmptyWarning()` — toggles `#empty-warning` based on `#option-rows` child count
   - On `DOMContentLoaded`: fetch `GET /option-groups/{{ object.pk }}/options/` → for each option call `buildRow` + `attachRowListeners` + append to `#option-rows` → call `updateEmptyWarning`
   - `#add-option` click: call `buildRow(null)` → `attachRowListeners` → append → `updateEmptyWarning` → focus first field
   - Save handler (group name): fetch `POST /option-groups/{{ object.pk }}/rename/` with `{name: input.value}` → on success disable Save button → on error show in `#group-name-error`
   - Save handler (option row, has `data-option-id`): fetch `POST /option-groups/{{ object.pk }}/options/<id>/update/` with `{name, instruction}` → on success disable Save → on error show field errors
   - Save handler (option row, no `data-option-id`): fetch `POST /option-groups/{{ object.pk }}/options/` with `{name, instruction}` → on success set `row.dataset.optionId` and disable Save → on error show field errors
   - Remove handler (has `data-option-id`): `confirm()` → fetch `POST /option-groups/{{ object.pk }}/options/<id>/delete/` → on success remove row, call `updateEmptyWarning`
   - Remove handler (no `data-option-id`): remove row from DOM, call `updateEmptyWarning`

### Success Criteria

#### Automated Verification

- Lint passes: `uv run ruff check .`

#### Manual Verification

- Create flow: `/option-groups/new/` → enter name → submit → redirect to edit page; page HTML contains no option rows
- Edit page initial load: `#option-rows` starts empty, then options appear after fetch
- Empty-group warning: shown while options are loading / when none exist; hidden once at least one option is present
- Rename group: edit name → Save → persisted; duplicate name → inline error
- Add option: click "Add option" → blank row appears → fill in → Save → row gains `data-option-id`
- Edit existing option: change field → Save enables → Save → persisted
- Delete existing option: Remove → `confirm()` → row disappears; warning shown if last
- Delete unsaved row: Remove → DOM removal, no network request
- Generate page: groups with no options do not appear

---

## Phase 3: Tests

### Overview

Remove obsolete formset tests, adjust `test_option_group_create` for the new redirect target, rewrite `test_option_group_update` as a rename test, and add coverage for all five new endpoints.

### Changes Required

#### 12. `tests/test_option_group_views.py`

**File**: `tests/test_option_group_views.py`

**Intent**: Align the test file with the new architecture.

**Contract**:

*Remove*:
- `formset_data` helper function
- `test_option_group_create_requires_at_least_one_option`
- `test_option_group_create_rejects_duplicate_option_names`

*Update*:
- `test_option_group_create` — POST only `{"name": "Style"}` (no formset data); assert redirect is to `/option-groups/<new_pk>/edit/`
- `test_option_group_update` → rename to `test_option_group_rename`; POST `json.dumps({"name": "Tone Updated"})` with `content_type="application/json"` to `/option-groups/<pk>/rename/`; assert 200 and `{"renamed": true}`
- `test_option_group_update_other_user_returns_404` → rename to `test_option_group_rename_other_user_returns_404`; use the rename endpoint

*Add*:
- `test_option_list` — GET `/option-groups/<group_pk>/options/`; assert 200, `options` key present, contains the expected option data
- `test_option_list_wrong_user_returns_404`
- `test_option_create` — POST `{"name": "Casual", "instruction": "Be casual."}` to `/option-groups/<pk>/options/`; assert 200, response has `id`
- `test_option_create_wrong_user_returns_404`
- `test_option_create_duplicate_name_returns_400`
- `test_option_update` — POST to `/option-groups/<group_pk>/options/<option_pk>/update/`; assert 200, `{"updated": true}`, DB reflects change
- `test_option_update_wrong_user_returns_404`
- `test_option_delete` — POST to `/option-groups/<group_pk>/options/<option_pk>/delete/`; assert 200, `{"deleted": true}`, option gone from DB
- `test_option_delete_wrong_user_returns_404`
- `test_option_delete_last_option_succeeds` — delete the only option; assert 200; assert group still exists with zero options

### Success Criteria

#### Automated Verification

- All tests pass: `uv run pytest`

#### Manual Verification

- All new test functions appear in `uv run pytest -v` output

---

## Testing Strategy

### Unit Tests

- List endpoint returns correct shape and only the requesting user's data
- Endpoint ownership: wrong-user requests return 404
- Validation: blank name, duplicate within group, duplicate group name on rename
- Create returns new option's `id` for the JS to use
- Delete of last option succeeds (empty group now allowed)

### Manual Testing Steps

1. Open `/option-groups/new/`, create a group, verify redirect to edit page
2. On the edit page, verify the HTML source has no option rows; verify they appear after the fetch
3. Add 2–3 options via "Add option" → Save per row; refresh → options persist
4. Edit an option's instruction → Save → refresh → change persisted
5. Delete one option → warning shown/hidden correctly
6. Go to `/` (generate page) → group appears; go back, delete all options → group disappears from generate page

---

## References

- Pattern for JSON function views: `core/views.py:146` (`generate_api`)
- Ownership queryset pattern: `core/views.py:97-102` (`OptionGroupUpdateView.get_queryset`)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands.

### Phase 1: Backend — REST endpoints + simplified views

#### Automated

- [ ] 1.1 Tests pass: `uv run pytest tests/test_option_group_views.py`
- [ ] 1.2 Lint passes: `uv run ruff check core/`

#### Manual

- [ ] 1.3 GET edit URL returns 200 with no option rows in HTML; POST returns 405
- [ ] 1.4 Create redirects to edit page; all five endpoints return correct JSON

### Phase 2: Template redesign

#### Automated

- [ ] 2.1 Lint passes: `uv run ruff check .`

#### Manual

- [ ] 2.2 Full create → add options → edit → delete flow works in browser
- [ ] 2.3 Generate page excludes empty groups
- [ ] 2.4 Edit page HTML source contains no option data; rows appear after fetch

### Phase 3: Tests

#### Automated

- [ ] 3.1 All tests pass: `uv run pytest`

#### Manual

- [ ] 3.2 All new test functions appear in `uv run pytest -v` output
