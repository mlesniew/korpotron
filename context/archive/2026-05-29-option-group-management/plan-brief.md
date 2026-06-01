# Option Group Management — Plan Brief

> Full plan: `context/changes/option-group-management/plan.md`

## What & Why

Build the CRUD management UI for `OptionGroup` and its child `Option` records (FR-004/005/006). Option groups are the mechanism that enforces mutually exclusive tone/style choices at generation time — without them the core workflow can't be configured, making this a must-have before the transformation flow can be built.

## Starting Point

`OptionGroup` and `Option` models are already defined and migrated. Template management (four CBVs, three templates, nav link, seven view tests) was completed in the prior change and establishes the exact pattern to follow. No views, URLs, or templates exist for option groups yet.

## Desired End State

A logged-in user can navigate to `/option-groups/`, create a new group with at least one inline option (name + instruction), edit and delete existing groups, and see a cascade warning on deletion. Option names within a group must be unique; violations are caught at form submission. "Option Groups" appears in the navbar alongside "Templates".

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Options management UX | Inline formset on OptionGroup form | Single-page workflow matches PRD intent of "create a group with a set of options" | Plan |
| Empty group validation | Require at least 1 option | An empty group contributes nothing at generation time | Plan |
| Option name uniqueness | Enforce unique names per group | Prevents confusing duplicates in the option picker | Plan |
| Delete confirmation | Show option count in warning | Prevents surprise cascade data loss | Plan |
| Scope | Management CRUD only | Parallel to template-management scope; transformation wiring is a separate change | Plan |

## Scope

**In scope:** `OptionGroup` List/Create/Update/Delete views, `Option` inline editing via InlineFormSet, `unique_together` constraint on `Option`, three HTML templates, navbar link, nine integration tests

**Out of scope:** Wiring option groups into the transformation workflow (FR-008), standalone Option CRUD routes, ordering control within a group, bulk import/export

## Architecture / Approach

New `core/forms.py` holds `RequiredOptionInlineFormSet` (minimum-one and unique-name validation) and the `OptionFormSet` factory. Four CBVs added to `core/views.py` follow the template-management pattern exactly; Create and Update override `get_context_data` and `form_valid` to handle the formset alongside the group form. A new `core/option_group_urls.py` is mounted at `path("option-groups/", ...)` in the root URL conf to avoid restructuring the existing template URL file.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Data Model, Views, URLs | Migration, 4 CBVs with formset, URL wiring | `form_valid` partial-save bug if formset and group save aren't properly sequenced |
| 2. HTML Templates and Nav | Usable UI end-to-end, nav link, dynamic add/remove rows JS | Inline formset row cloning JS requires correct `__prefix__` replacement |
| 3. Tests | 9 integration tests covering happy path, security, and formset rules | Formset management form keys are non-obvious; missing them causes silent test failures |

**Prerequisites:** None — models and migrations already exist; no external dependencies required
**Estimated effort:** ~1-2 sessions across 3 phases

## Open Risks & Assumptions

- The `unique_together` constraint migration will fail if the dev DB has existing duplicate-named options in the same group (clean dev DB assumed)
- Dynamic row JS assumes no other JavaScript framework is loaded; adding htmx or Alpine later may require revisiting the approach

## Success Criteria (Summary)

- User can create, edit, and delete option groups with inline options through the UI at `/option-groups/`
- Duplicate option names within a group and empty groups are rejected with a form error
- All 9 integration tests pass; full test suite green; Docker build passes
