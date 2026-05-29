# Template Management Implementation Plan

## Overview

Build user-facing CRUD views for the `Template` model: list, create, edit, and delete. Each view is protected by `login_required` and scoped to the authenticated user's own templates. A "Templates" link is added to the nav bar for persistent access.

## Current State Analysis

- `Template` model exists (`core/models.py`) with `user`, `name`, `base_prompt`, `generate_title` fields and a migration applied.
- No user-facing views exist for templates — only Django admin.
- `korpotron/views.py` has a single `home` view; `korpotron/urls.py` has no template-management routes.
- `templates/base.html` has a nav bar with only a logout button.
- `core/` has no `urls.py` or `views.py`.

## Desired End State

A logged-in user can navigate to `/templates/` via a nav bar link and see a list of their templates. From there they can create a new template, edit an existing one, or delete one. All redirects after CRUD actions land on the list. Users cannot see or modify another user's templates.

### Key Discoveries

- `core/models.py:6-19` — `Template` model; `user` FK with `CASCADE`, `ordering = ["name"]`.
- `templates/base.html:10-18` — nav bar; logout button is the only nav element.
- `korpotron/urls.py:22-26` — `path("admin/")` and `path("")`; no app-level URL include yet.
- Test fixtures in `tests/conftest.py:6-7` — `user` fixture creates `username="tester"`.
- Existing tests in `tests/test_auth.py` — pattern to follow for view tests.

## What We're NOT Doing

- No read-only template detail page — list is the entry point, clicking a template goes straight to edit.
- No `is_response` field — deferred to v2 per PRD decision (FR-010 is nice-to-have, response functionality out of scope for MVP).
- No option group association in this change — that belongs to `option-group-management` and `text-generation-flow`.
- No pagination — personal tool with small template counts.

## Implementation Approach

Use Django class-based views (`LoginRequiredMixin` + `ListView`, `CreateView`, `UpdateView`, `DeleteView`) in a new `core/views.py`. Each view overrides `get_queryset()` to filter by `request.user`. A new `core/urls.py` is included under the `templates/` prefix in the root urlconf. Three Django HTML templates handle list, form (shared create/edit), and delete confirmation. The nav bar in `base.html` gets a single "Templates" link.

## Phase 1: Views and URLs

### Overview

Wire up the four class-based views and URL patterns. No HTML templates yet — this phase is backend-only and verifiable via tests and Django's dev server returning responses (even unstyled).

### Changes Required

#### 1. `core/views.py` — new file

**File**: `core/views.py`

**Intent**: Define four class-based views for Template CRUD. Each mixes in `LoginRequiredMixin` and scopes `get_queryset()` to `request.user` so users cannot access each other's templates.

**Contract**:
- `TemplateListView(LoginRequiredMixin, ListView)` — `model = Template`, `get_queryset` returns `Template.objects.filter(user=request.user)`.
- `TemplateCreateView(LoginRequiredMixin, CreateView)` — `model = Template`, `fields = ["name", "base_prompt", "generate_title"]`, `success_url = reverse_lazy("template-list")`, `form_valid` sets `form.instance.user = request.user` before saving.
- `TemplateUpdateView(LoginRequiredMixin, UpdateView)` — same fields and `success_url`, `get_queryset` filters by `request.user`.
- `TemplateDeleteView(LoginRequiredMixin, DeleteView)` — `success_url = reverse_lazy("template-list")`, `get_queryset` filters by `request.user`.

#### 2. `core/urls.py` — new file

**File**: `core/urls.py`

**Intent**: Define URL patterns for the four template views under a `templates/` prefix.

**Contract**:
- `path("", TemplateListView.as_view(), name="template-list")`
- `path("new/", TemplateCreateView.as_view(), name="template-create")`
- `path("<int:pk>/edit/", TemplateUpdateView.as_view(), name="template-update")`
- `path("<int:pk>/delete/", TemplateDeleteView.as_view(), name="template-delete")`

#### 3. `korpotron/urls.py` — add include

**File**: `korpotron/urls.py`

**Intent**: Mount the core URL patterns at `/templates/`.

**Contract**: Add `path("templates/", include("core.urls"))` to `urlpatterns`.

### Success Criteria

#### Automated Verification

- Lint passes: `uv run ruff check .`
- Type checking passes: `uv run mypy .` (if wired)

#### Manual Verification

- `uv run manage.py runserver` starts without errors.
- Visiting `/templates/` while logged in returns a response (even an unstyled or template-not-found error is fine at this stage — it confirms the view resolved).
- Visiting `/templates/` while not logged in redirects to `/accounts/login/`.

**Implementation Note**: After completing this phase and all automated verification passes, pause for manual confirmation before proceeding to Phase 2.

---

## Phase 2: HTML Templates and Nav

### Overview

Add the three Django HTML template files for list, form, and delete confirmation. Update `base.html` to add the "Templates" nav link.

### Changes Required

#### 1. `templates/base.html` — add Templates nav link

**File**: `templates/base.html`

**Intent**: Add a "Templates" link in the nav bar so users can reach template management from any page.

**Contract**: Inside the `<nav>`, add an `<a class="nav-link text-white" href="{% url 'template-list' %}">Templates</a>` element, visible only to authenticated users (inside the existing `{% if user.is_authenticated %}` block or alongside it).

#### 2. `templates/core/template_list.html` — new file

**File**: `templates/core/template_list.html`

**Intent**: Show the authenticated user's templates in a table with edit and delete links, plus a "New template" button.

**Contract**: Extends `base.html`. Iterates `object_list`. Each row shows `template.name`, a link to `template-update` with the template's `pk`, and a link to `template-delete`. An empty-state message is shown when there are no templates. A "New template" button links to `template-create`.

#### 3. `templates/core/template_form.html` — new file

**File**: `templates/core/template_form.html`

**Intent**: Shared form for both create and update. Renders all editable fields and submits via POST.

**Contract**: Extends `base.html`. Renders `{{ form.as_p }}`. Submit button label should be "Save". Includes a cancel link back to `template-list`.

#### 4. `templates/core/template_confirm_delete.html` — new file

**File**: `templates/core/template_confirm_delete.html`

**Intent**: Confirm deletion of a template before committing.

**Contract**: Extends `base.html`. Shows the template name. Provides a POST form with a "Delete" submit button and a cancel link back to `template-list`.

### Success Criteria

#### Automated Verification

- Lint passes: `uv run ruff check .`
- Tests pass: `uv run pytest`

#### Manual Verification

- "Templates" link appears in the nav bar for logged-in users.
- Template list page renders with the user's templates (or empty state).
- "New template" form submits and redirects to the list.
- Edit form pre-populates the existing values and saves correctly.
- Delete confirmation page shows the template name; confirming removes it and returns to the list.

**Implementation Note**: After completing this phase and all automated verification passes, pause for manual confirmation before proceeding to Phase 3.

---

## Phase 3: Tests

### Overview

Add integration tests for all four views covering the happy path and the two security guards: auth redirect and cross-user ownership isolation.

### Changes Required

#### 1. `tests/test_template_views.py` — new file

**File**: `tests/test_template_views.py`

**Intent**: Cover the full CRUD surface for the template management views — successful operations, unauthenticated redirects, and cross-user isolation — following the test style in `tests/test_auth.py`.

**Contract**: Use `@pytest.mark.django_db`, the `client` fixture, and the `user` fixture from `conftest.py`. Create a second user fixture inline (or a helper) for ownership isolation tests. The test scenarios:

- `test_template_list_requires_login` — GET `/templates/` without auth → 302 to login.
- `test_template_list_shows_only_own` — authenticated user sees their templates but not another user's.
- `test_template_create` — POST to `/templates/new/` with valid data creates a `Template` owned by the logged-in user and redirects to `/templates/`.
- `test_template_update` — POST to `/templates/<pk>/edit/` with new name updates the template and redirects to `/templates/`.
- `test_template_delete` — POST to `/templates/<pk>/delete/` removes the template and redirects to `/templates/`.
- `test_template_update_other_user_returns_404` — authenticated user POSTing to another user's template edit URL gets 404.
- `test_template_delete_other_user_returns_404` — same for delete URL.

### Success Criteria

#### Automated Verification

- All tests pass: `uv run pytest`
- Lint passes: `uv run ruff check .`

#### Manual Verification

- Test output shows all new tests as `PASSED` with no warnings.

**Implementation Note**: After completing this phase and all automated verification passes, confirm final manual testing before marking the change complete.

---

## Testing Strategy

### Integration Tests

End-to-end Django test client tests covering the four views. See Phase 3 details.

### Manual Testing Steps

1. Create a template via `/templates/new/` — verify it appears in the list.
2. Edit the template — verify changes persist after redirect.
3. Delete the template — verify it disappears from the list.
4. Log out and attempt to visit `/templates/` — verify redirect to login.
5. Create two users via Django admin; log in as user A, visit user B's template URL directly — verify 404.

## Migration Notes

No migrations required — `Template` model and its existing migration are unchanged.

## References

- Roadmap entry: `context/foundation/roadmap.md` (S-01)
- PRD functional requirements: `context/foundation/prd.md` (FR-001, FR-002, FR-003)
- Core models: `core/models.py`
- Auth test pattern: `tests/test_auth.py`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Views and URLs

#### Automated

- [ ] 1.1 Lint passes: `uv run ruff check .`

#### Manual

- [ ] 1.2 Dev server starts without errors
- [ ] 1.3 `/templates/` while logged in returns a response
- [ ] 1.4 `/templates/` while not logged in redirects to login

### Phase 2: HTML Templates and Nav

#### Automated

- [ ] 2.1 Lint passes: `uv run ruff check .`
- [ ] 2.2 Tests pass: `uv run pytest`

#### Manual

- [ ] 2.3 "Templates" nav link appears for logged-in users
- [ ] 2.4 Template list renders correctly (with templates and empty state)
- [ ] 2.5 Create form submits and redirects to list
- [ ] 2.6 Edit form pre-populates and saves correctly
- [ ] 2.7 Delete confirmation removes template and redirects to list

### Phase 3: Tests

#### Automated

- [ ] 3.1 All tests pass: `uv run pytest`
- [ ] 3.2 Lint passes: `uv run ruff check .`

#### Manual

- [ ] 3.3 All new tests show as PASSED with no warnings
