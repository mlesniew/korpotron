# Template Management — Plan Brief

> Full plan: `context/changes/template-management/plan.md`

## What & Why

Build the user-facing CRUD interface for templates (FR-001 to FR-003). Currently templates can only be managed via Django admin — there are no app-facing views, URLs, or HTML templates. This change gives users a proper UI to create, edit, and delete their templates.

## Starting Point

The `Template` model (`core/models.py`) exists with a migration applied. Auth, login_required, and Bootstrap 5 are in place. The home page is a placeholder; the nav bar has only a logout button. There are no views or URLs in the `core` app.

## Desired End State

A logged-in user sees a "Templates" link in the nav bar. Clicking it shows their list of templates with create, edit, and delete actions. All mutations redirect back to the list. Users cannot see or touch another user's templates.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
|---|---|---|
| `is_response` model field | Deferred to v2 | Response functionality is out of scope for MVP (FR-010 is nice-to-have) |
| Navigation entry point | Nav bar link | Persistent access from every page; matches Bootstrap nav pattern already in place |
| Detail view | None — list → edit directly | Edit form is the natural place to see template content; detail page adds a screen for no gain |
| Post-action redirect | Template list after all three actions | Predictable and consistent; user always returns to their full overview |
| Test coverage | Happy path + auth redirect + cross-user isolation | Covers the security surface that matters without over-testing Django internals |

## Scope

**In scope:**
- `core/views.py` — four class-based views (list, create, update, delete)
- `core/urls.py` — URL patterns under `/templates/`
- Root urlconf include at `/templates/`
- Three Django HTML template files (list, form, confirm-delete)
- Nav bar "Templates" link in `base.html`
- Integration tests for all views

**Out of scope:**
- `is_response` field (deferred)
- Option group association (belongs to `option-group-management`)
- Pagination
- Read-only detail view

## Architecture / Approach

Standard Django class-based views with `LoginRequiredMixin`. Each view overrides `get_queryset()` to filter by `request.user`, ensuring cross-user isolation at the ORM layer. The `create` view sets `form.instance.user = request.user` in `form_valid`. A new `core/urls.py` is included in the root urlconf under the `templates/` prefix.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Views and URLs | Backend CRUD wired and routable | Forgetting to filter by `request.user` in all write views |
| 2. HTML Templates + Nav | Fully functional UI in the browser | Template naming collision (`Template` model vs Django templates directory) |
| 3. Tests | Auth and ownership guards verified | Ownership isolation test needs a second user — conftest only provides one |

**Prerequisites:** F-01 (auth-scaffold) and F-02 (core-data-model) — both `ready` per roadmap.
**Estimated effort:** ~1 session across 3 phases.

## Open Risks & Assumptions

- The Django template directory for `core` views will be `templates/core/` — this is the conventional pattern and will be found automatically via the `DIRS: [BASE_DIR / "templates"]` entry in settings (not APP_DIRS, which would look in `core/templates/`).
- No `mypy` CI gate exists yet; type hints should still be added per CLAUDE.md convention but won't be machine-verified this change.

## Success Criteria (Summary)

- Authenticated user can complete the full create → edit → delete cycle via the browser UI.
- Unauthenticated GET/POST to any `/templates/` URL redirects to login.
- Authenticated user gets 404 when accessing another user's template URLs.
