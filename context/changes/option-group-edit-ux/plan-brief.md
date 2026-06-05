# Option Group Edit UX — Plan Brief

> Full plan: `context/changes/option-group-edit-ux/plan.md`

## What & Why

The current option-group editing page uses Django formsets: users edit all options and submit one big POST. The delete mechanic is a checkbox (Django formset default) and the fields are unstyled `<p>` tags. The new UX exposes a full REST API for options (list, create, update, delete) plus group rename, and makes the edit page a static shell — no server-side option rendering. All option data is fetched and managed client-side via JavaScript.

## Starting Point

`optiongroup_form.html` renders all option rows server-side with `{{ option_form.as_p }}` and a DELETE checkbox per row. `OptionGroupUpdateView` is an `UpdateView` that processes an `OptionFormSet` atomically. The generate page (`HomeView`) passes all groups to the template, including empty ones. There are no JSON endpoints for option management today.

## Desired End State

Five REST endpoints cover all option-group operations. The edit page at `/option-groups/<pk>/edit/` is a static `DetailView` shell — the HTML contains no option data. On page load, JS fetches `GET /option-groups/<pk>/options/` and renders rows dynamically. Each row has its own Save and Remove buttons. Save fires a PATCH/POST; Remove (on saved rows) confirms then calls the delete endpoint. Adding an option appends a blank row; Save POSTs to create, and on success the row gains an ID. Empty groups are allowed — the edit page shows a warning; the generate page filters them out server-side.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| API surface | Full REST: list + create + update + delete + group rename | User confirmed all option management should happen via REST endpoints | Plan |
| Edit page rendering | Static shell — options fetched client-side via JS | Follows naturally from having a dedicated list endpoint; no server-side option rendering | Plan |
| Saved-row delete | confirm() → AJAX → DOM removal | Immediate feedback with accidental-delete protection | Plan |
| Unsaved-row delete | DOM removal only, no AJAX | Row was never persisted; no server round-trip needed | Plan |
| New row save | Inline Save button → POST to create endpoint | Consistent UI pattern across new and existing rows | Plan |
| Last-option deletion | Allowed — empty groups permitted | User asked to allow empty groups; generate page filters them out instead | Plan |
| Empty groups on generate | Server-side filter in `HomeView` queryset | No dead markup in the browser; consistent with page-load model | Plan |
| Create flow | Standard form POST for name only → redirect to edit page | Simplest path to get a group PK before adding options via AJAX | Plan |
| CSRF for AJAX | Read `csrftoken` cookie | Django standard pattern; edit page has no `<form>` element | Plan |
| Testing | Update + add endpoint tests; no browser tests | No test-infra investment justified for this change | Plan |

## Scope

**In scope:**
- Five REST endpoints: list options, create option, update option, delete option, rename group
- Simplified `OptionGroupCreateView` (no formset; redirects to edit page)
- `OptionGroupUpdateView` converted to `DetailView` (static shell, no `prefetch_related`)
- `optiongroup_form.html` rebuilt as a static shell with inline JS that fetches + renders options
- `HomeView` filters empty groups from generate page
- Tests for all new endpoints

**Out of scope:**
- Option reordering / drag-and-drop
- Bulk-edit requests
- Browser/Playwright tests for JS behaviour
- `OptionGroupDeleteView` (group-level delete unchanged)
- `OptionGroupListView` (unchanged)

## Architecture / Approach

Five new function views follow the existing `generate_api` pattern (`@login_required`, mutation endpoints use `@require_POST`, `json.loads(request.body)`, `JsonResponse`). The list endpoint is GET-only. Ownership is enforced via `get_object_or_404` with user filter. The edit page is a static `DetailView` shell; `optiongroup_form.html` carries all JS inline (vanilla JS, no framework). On `DOMContentLoaded` JS fetches the list endpoint and builds rows dynamically; a delegated `input` listener on `#option-rows` handles all rows uniformly.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Backend | 5 REST endpoints, simplified views, empty-group filter | Ownership check pattern must be consistent or tests will miss a gap |
| 2. Template | Static shell + inline JS that fetches and renders options | JS correctness isn't covered by automated tests — needs careful manual testing |
| 3. Tests | Endpoint coverage + updated create/rename tests | Old formset tests must be cleanly removed to avoid 405 confusion |

**Prerequisites:** None — purely additive backend plus a template rewrite.  
**Estimated effort:** ~2 focused sessions across 3 phases.

## Open Risks & Assumptions

- The edit page's JS is untested by the automated suite — any behaviour regression in the browser flow would only be caught manually.
- The `DetailView` returning 405 on POST is a behaviour change; existing formset tests that POST to the edit URL will need to be updated (covered in Phase 3).
- The edit page makes a network request on every load — a slow or failing list endpoint will result in a blank option list rather than an error page.

## Success Criteria (Summary)

- Every option-group mutation (add, edit, delete option; rename group) completes without a page reload
- Empty groups no longer appear on the generate page
- All `uv run pytest` tests pass with the updated and new endpoint tests
