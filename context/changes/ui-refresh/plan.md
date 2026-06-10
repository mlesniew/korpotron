# UI Refresh Implementation Plan

## Overview

Recreate the seven high-fidelity prototypes in `context/changes/ui-refresh/design_handoff/`
as the project's Django templates. The app **stays on raw Bootstrap 5** (grid + utilities,
CDN as today) and layers a bespoke design system on top via a new
`static/css/korpotron.css` (oklch colour tokens, IBM Plex typography, custom components:
pill buttons, CSS-only toggle, delete dialog, output card, frosted-glass nav). No CSS
framework swap. No data-model changes. SSR and the existing vanilla-JS approach are
preserved throughout.

This is a redesign, not a rewrite of behaviour: every URL name, view, model, and the
`generate-api` JSON contract stay the same, with one deliberate exception — the two
`DeleteView`s switch from a redirect to a `204 No Content` so the list pages can delete a
row via `fetch()` without a full reload.

## Current State Analysis

Small, cohesive Django SSR app. Bootstrap 5.3.3 loaded from jsDelivr in two places
(`base.html:7` and the standalone `landing.html:7`); **no `static/` dir or project CSS
exists yet**; all styling is inline Bootstrap classes; interactivity is hand-written
vanilla JS. WhiteNoise serves static files in production via
`CompressedManifestStaticFilesStorage`, with `collectstatic` run in the Dockerfile —
so any new stylesheet must live under a collected static root and be referenced with
`{% static %}`.

Key constraints discovered:

- **No `STATICFILES_DIRS`** is set (`korpotron/settings.py`), and there is no `static/`
  dir. A project-level `static/css/korpotron.css` will not be collected until
  `STATICFILES_DIRS = [BASE_DIR / "static"]` is added.
- **The generate API URL name is `generate-api`** (`core/urls.py:18`), not `generate` as
  the handoff README writes it. The JSON contract itself matches `generate_api` exactly
  (`core/views.py:146`): `POST {template_id, option_ids: [...], text}` →
  `200 {title, body}` / `4xx|5xx {error}`.
- **`HomeView` ignores query params** (`core/views.py:131`), so the handoff's "Use →"
  deep-link (`home?template=pk`) has no server support. Preselection is handled in JS on
  the generate page (read `?template=` and activate the matching pill).
- **`landing.html` does not extend `base.html`** and duplicates the Bootstrap `<link>`
  (`landing.html:7`). Both anonymous pages (landing, login) need the shared design assets
  (fonts + `korpotron.css`) without inheriting the authenticated nav.
- **Login is wired through Django's `LoginView`** (`korpotron/urls.py` includes
  `django.contrib.auth.urls`; `LOGIN_URL=/accounts/login/`, `LOGIN_REDIRECT_URL=/`).
  `registration/login.html` exists and is rendered on both GET and on failed POST.
- **The generate page is the JS-coupled hotspot** (`generate.html:64-204`): fetch to
  `generate-api`, button-group toggle, clipboard with `execCommand` fallback,
  `AbortController` 65s timeout. The redesign reworks its markup and state machine but
  must preserve this contract and these behaviours.
- **The modifier formset JS** (`optiongroup_form.html:64-96`) clones `__prefix__`
  rows and bumps `id_options-TOTAL_FORMS`; restyle it, keep the mechanics.
- **Forms are unstyled today** (`{{ form.as_p }}` in `template_form`, `optiongroup_form`,
  `login`). The redesign replaces `as_p` with bespoke markup wired to individual form
  fields — no crispy-forms / widget-tweaks dependency is introduced.

## Desired End State

All seven screens match the `design_handoff/` prototypes pixel-closely (colours,
fonts, radii, shadows, interaction states), wired to real Django template tags, form
rendering, URL reversals, CSRF, and the existing formset/generate JS. Specifically:

- A new `static/css/korpotron.css` holds the design tokens, IBM Plex typography, and all
  custom component classes; loaded from a shared head after Bootstrap.
- `base.html` has a frosted-glass sticky nav with the `KORPOTRON™` mono brand and a
  "Modifiers" label (URLs/models unchanged).
- Landing page is a dark hero with a login **modal**; the standalone login page is a
  designed dark card that renders `form.errors` in an error bar; a failed login lands on
  that standalone page (default Django behaviour).
- Templates and Modifiers lists are card layouts with a shared custom delete dialog that
  POSTs via `fetch()` and fades the row out on `204`.
- Template and Modifier forms are bespoke (toggle switch, two-column formset grid).
- The generate page is a single-column workspace with a stateful
  input → loading (rotating quips) → output transition, Edit/Regenerate, and copy.

**Verification:** `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run manage.py check`, and `uv run manage.py collectstatic --noinput` all pass; and a
manual walkthrough of each screen (ideally via `playwright-cli` screenshots against
`runserver`) matches the prototypes and exercises every interaction.

### Key Discoveries:

- `korpotron/settings.py` — add `STATICFILES_DIRS = [BASE_DIR / "static"]`; manifest
  storage means `{% static %}` is mandatory and `collectstatic` must resolve every ref.
- `core/urls.py:18` — generate URL name is `generate-api`; `core/views.py:146` is the
  contract to preserve.
- `core/views.py:54-59,123-128` — the two `DeleteView`s to switch to `204`.
- `core/forms.py` — `OptionFormSet` (`inlineformset_factory`, `extra=0`, `can_delete=True`,
  `RequiredOptionInlineFormSet` enforces ≥1 option + unique names); the bespoke formset
  markup must keep its hidden fields, `DELETE`, and management form intact.
- `templates/core/generate.html:64-204` and `optiongroup_form.html:64-96` — the two JS
  blocks to rework while preserving their contracts.

## What We're NOT Doing

- **No CSS framework swap** — raw Bootstrap 5 stays; the framework comparison in
  `research.md` is historical only.
- **No data-model / migration changes** — `Template`, `OptionGroup`, `Option`,
  `DailyGenerationCount`, `OnboardingState` untouched.
- **No change to the `generate-api` request/response contract or the LLM flow.**
- **No crispy-forms or django-widget-tweaks** dependency — forms are hand-built markup.
- **No URL-name or model renames** — "Option Groups → Modifiers" is a display-label
  change only.
- **No support for a no-JS delete path** — the GET confirm-delete pages are removed; JS
  is assumed enabled.
- **No dark-mode / theming system** — out of scope per the research's scope decisions.
- **No new tests for view logic** beyond keeping the existing suite green (this is a
  template/CSS/JS change). The one backend tweak — DeleteView → 204 — is covered by a
  small added test.

## Implementation Approach

Build the shared substrate first, then the screens in increasing order of risk:
foundation/shell → landing+login → lists/forms/delete → the JS-heavy generate page.
Each phase leaves the app fully working and visually consistent so it can be verified in
isolation. Custom CSS lives entirely in `static/css/korpotron.css`; templates use
Bootstrap grid/utilities plus the new `k-*` component classes. All JS stays vanilla and
inline in its template (matching today's pattern), except where a behaviour is shared
across pages (the delete dialog), which lives in a small reusable include.

The handoff `.html` files are **design references, not production code** — recreate their
look and interactions, but never copy their dummy-data markup or prototype-only JS.

## Critical Implementation Details

- **Static assets must use `{% static %}`** and survive `collectstatic` under manifest
  storage. After adding `korpotron.css`, run `collectstatic` as part of verification — a
  missing/misspelled `{% static %}` path fails the build, not just the page.
- **Shared head for anonymous pages.** `base.html`, `landing.html`, and
  `registration/login.html` all need the IBM Plex fonts + `korpotron.css`. Factor the
  `<link>`s into a small `templates/_head.html` partial included by all three, so the CDN
  and asset references live in one place (resolving the existing "version must match
  base.html" duplication between `base.html:7` and `landing.html:7`).
- **Delete returns 204, so success_url is irrelevant.** The list JS owns the post-delete
  UI (row fade-out); the view must not redirect. CSRF travels as the `X-CSRFToken` header
  read from the `csrftoken` cookie (same pattern already in `generate.html:70-73`).
- **Generate state machine.** Loading and output states replace the input region in place
  (single column). "← Edit text" must restore the textarea with its previous content
  intact; "↻ Regenerate" re-runs with the same input + current selections. Only one
  request in flight at a time (preserve the `inFlight` guard).

---

## Phase 1: Design system foundation & app shell

### Overview

Stand up the shared design system and the global navigation so every subsequent screen
inherits the new look. After this phase the authenticated pages already render with the
new fonts, colours, and nav, even though their bodies are still the old markup.

### Changes Required:

#### 1. Static files setting

**File**: `korpotron/settings.py`

**Intent**: Register a project-level static source so `static/css/korpotron.css` is found
by the dev server and collected in production.

**Contract**: Add `STATICFILES_DIRS = [BASE_DIR / "static"]`. No other static settings
change.

#### 2. Design-system stylesheet

**File**: `static/css/korpotron.css` (new)

**Intent**: Hold every design token and custom component class the redesign needs, so
templates stay on Bootstrap utilities + these classes. Sourced from the token table and
component specs in `design_handoff/README.md`.

**Contract**: A `:root` block with the palette / text / accent / nav / danger / success
colours, radii (`--k-r`, `--k-r-lg`, `--k-r-xl`), and shadows exactly as listed in the
handoff README; `body` font set to IBM Plex Sans and a `.k-mono` helper for IBM Plex
Mono. Plus the custom component classes used across screens: frosted sticky nav, pill
buttons (`.tmpl-btn` + active state), CSS-only toggle switch (`.k-toggle-input` /
`.k-toggle-track`), delete dialog (`.k-del-overlay` / `.k-del-dialog` / `.k-del-actions` /
`.k-btn-danger`), output card, bespoke form inputs/labels, list cards/rows, breadcrumbs,
error bars, and accent/ghost buttons. Bootstrap variables are overridden here where they
conflict (this file loads after Bootstrap).

#### 3. Shared head partial

**File**: `templates/_head.html` (new)

**Intent**: Single source of truth for the head assets shared by base + the two anonymous
pages.

**Contract**: Emits the `<meta>` charset/viewport, `<title>`, the Bootstrap CDN `<link>`
(with its SRI hash), the Google Fonts preconnect + IBM Plex `<link>`, and
`<link rel="stylesheet" href="{% static 'css/korpotron.css' %}">` **after** Bootstrap.
Requires `{% load static %}`.

#### 4. Base template & navigation

**File**: `templates/base.html`

**Intent**: Adopt the frosted-glass sticky nav and shared head; rename the visible
"Option Groups" link to "Modifiers".

**Contract**: Include `_head.html` in `<head>`. Replace the dark Bootstrap navbar with the
handoff's sticky frosted nav: `KORPOTRON™` brand in IBM Plex Mono (links to `home`),
nav links Generate / Templates / **Modifiers** (→ `option-group-list`, name unchanged),
and the styled logout form. Keep the `{% block content %}` container.

### Success Criteria:

#### Automated Verification:

- Django check passes: `uv run manage.py check`
- Static files collect cleanly: `uv run manage.py collectstatic --noinput`
- Lint passes: `uv run ruff check .`
- Format check passes: `uv run ruff format --check .`
- Existing tests pass: `uv run pytest`

#### Manual Verification:

- Authenticated pages render with the frosted nav, IBM Plex fonts, and new background;
  brand reads `KORPOTRON™`, the third nav item reads "Modifiers".
- No browser console errors; `korpotron.css` and fonts load (200s) on `runserver`.
- Nav active/hover states behave per the design.

**Implementation Note**: After completing this phase and all automated verification
passes, pause for manual confirmation before proceeding.

---

## Phase 2: Landing page & login

### Overview

Rebuild the anonymous entry points: the dark landing hero with an embedded login modal,
and the designed standalone login page that handles failed logins.

### Changes Required:

#### 1. Landing page

**File**: `templates/core/landing.html`

**Intent**: Recreate the dark hero with feature tiles and an in-page login modal, loading
shared assets without the authenticated nav.

**Contract**: Standalone page (does not extend `base.html`) including `_head.html`.
Full-viewport dark hero with the CSS grid overlay + amber radial glow (pure CSS), a fixed
frosted nav (brand + "Log in" button), hero copy, and three bordered feature tiles. A
login **modal overlay** containing a form that POSTs to `{% url 'login' %}` with
`{% csrf_token %}` and `username`/`password` inputs; opened by both the nav "Log in" and
the hero CTA; closes on Esc or backdrop click. Inline vanilla JS for open/close only.

#### 2. Standalone login page

**File**: `templates/registration/login.html`

**Intent**: Replace the `{{ form.as_p }}` login with the designed dark card that Django
serves on GET and on failed POST.

**Contract**: Recreate `design_handoff/Korpotron Login.html` as a Django template:
brand-only nav, centred login card (title + subtitle, `username`/`password` fields,
mono submit button, back-to-home link), all on the shared dark background. Form POSTs to
`{% url 'login' %}` with `{% csrf_token %}`. The error bar renders only when the auth form
has errors (`{% if form.errors %}` / `form.non_field_errors`) — wired to real Django form
state, not the prototype's `onclick` demo toggle.

### Success Criteria:

#### Automated Verification:

- Django check passes: `uv run manage.py check`
- Templates render without errors (smoke): `uv run pytest`
- Lint passes: `uv run ruff check .`

#### Manual Verification:

- Anonymous `/` shows the new landing; login modal opens from both triggers and closes on
  Esc and backdrop click.
- A valid login redirects to the generate page; an invalid login shows the standalone
  login page with the error bar populated.
- Visiting a protected URL while logged out redirects to the designed standalone login.
- Landing and login match the prototypes (hero glow/grid, card, fonts).

**Implementation Note**: After completing this phase and all automated verification
passes, pause for manual confirmation before proceeding.

---

## Phase 3: Lists, forms & delete flow

### Overview

Rebuild the Templates and Modifiers list and form screens, and switch deletion to a
JS-driven dialog that POSTs and removes the row in place.

### Changes Required:

#### 1. DeleteViews return 204

**File**: `core/views.py`

**Intent**: Let the list pages delete via `fetch()` without a redirect or confirm page.

**Contract**: In `TemplateDeleteView` and `OptionGroupDeleteView`, override the deletion
to perform the delete and return `HttpResponse(status=204)` instead of redirecting
(keep the per-user `get_queryset` ownership filter so a missing/again-foreign pk yields a
404). `success_url` becomes unused.

#### 2. Remove confirm-delete templates

**Files**: `templates/core/template_confirm_delete.html`,
`templates/core/optiongroup_confirm_delete.html` (delete both)

**Intent**: No GET-confirmation step remains; the JS dialog is the only delete path.

**Contract**: Files removed. No view references them after change #1.

#### 3. Shared delete dialog include

**File**: `templates/core/_delete_dialog.html` (new)

**Intent**: One delete-dialog markup + JS, reused by both list pages.

**Contract**: The `.k-del-overlay` dialog markup (title, name slot, Cancel + red Delete)
plus a small vanilla script exposing a way for a list row's Delete button to open the
dialog with the target's name and delete URL. On confirm it `fetch()`-POSTs to that URL
with the `X-CSRFToken` header (cookie-derived), and on a 2xx fades out and removes the
originating row; on failure it surfaces an inline message. Closes on Cancel/backdrop.

#### 4. Templates list

**File**: `templates/core/template_list.html`

**Intent**: Card-list layout per the handoff with per-row actions and the delete dialog.

**Contract**: Header with title + template count and a "+ New template" accent button.
A bordered card whose rows show name + optional "Generates title" badge (when
`template.generate_title`) + truncated `base_prompt` preview, and right-aligned actions:
"Use →" → `{% url 'home' %}?template={{ template.pk }}`, "Edit" →
`{% url 'template-update' template.pk %}`, and a Delete button wired to the shared dialog
(`{% url 'template-delete' template.pk %}`). Dashed empty-state card when none. Includes
`_delete_dialog.html`.

#### 5. Modifiers list

**File**: `templates/core/optiongroup_list.html`

**Intent**: Same card layout as Templates, labelled "Modifiers", showing option pills.

**Contract**: Mirrors the Templates list. Each row shows the group name + neutral pills
for each `Option.name`, with Edit (`option-group-update`) and a dialog-wired Delete
(`option-group-delete`). "Modifiers" wording throughout; URLs/models unchanged. Dashed
empty state. Includes `_delete_dialog.html`.

#### 6. Template form

**File**: `templates/core/template_form.html`

**Intent**: Bespoke form card replacing `{{ form.as_p }}`, with a toggle switch for
`generate_title`.

**Contract**: Breadcrumb ("Templates › New/Edit template"), centred card. Name input
(`form.name`), Prompt textarea (`form.base_prompt`) with the right-aligned hint, and the
CSS-only toggle switch bound to `form.generate_title` (checkbox `name`/`id`/checked state
from the bound field). Save (accent) + Cancel (ghost → `template-list`). Render each
field's errors inline. Markup is hand-built but uses the form fields' real names/ids so
the existing `CreateView`/`UpdateView` keep working unchanged.

#### 7. Modifier form

**File**: `templates/core/optiongroup_form.html`

**Intent**: Bespoke form with the two-column options formset grid, restyled add/delete JS.

**Contract**: Breadcrumb, wider card. Name input (`form.name`). `{{ formset.management_form }}`
plus column headers ("Label" / "Instruction injected into prompt") and one grid row per
option form (`grid-template-columns: 180px 1fr 32px`): name input, instruction textarea,
× delete button; preserve each form's hidden fields and `DELETE` checkbox. An
`<template>` empty-row for cloning and a dashed "+ Add option" button. The add/delete JS
follows the existing `optiongroup_form.html:64-96` pattern (clone `__prefix__`, bump
`id_options-TOTAL_FORMS`, check `DELETE` + hide on remove) — restyled, same mechanics.
Render `formset.non_form_errors` and per-field errors.

### Success Criteria:

#### Automated Verification:

- Existing + new tests pass: `uv run pytest` (incl. a test that a POST to a delete URL
  removes the object and returns 204)
- Django check passes: `uv run manage.py check`
- Lint passes: `uv run ruff check .`
- Format check passes: `uv run ruff format --check .`

#### Manual Verification:

- Creating/editing a Template works; the `generate_title` toggle reflects and saves state.
- Creating/editing a Modifier works; adding and deleting option rows works; submitting
  with zero options or duplicate names shows the formset errors.
- The delete dialog opens with the right name, deletes on confirm (row fades out, no
  reload), and cancels/backdrop-closes cleanly on both list pages.
- Empty states render for both lists.

**Implementation Note**: After completing this phase and all automated verification
passes, pause for manual confirmation before proceeding.

---

## Phase 4: Generate workspace

### Overview

Rebuild the interactive heart: pill-based selectors and a single-column workspace whose
input state transitions to a loading state and then an output card, with Edit/Regenerate.
The `generate-api` contract and all existing JS safeguards are preserved.

### Changes Required:

#### 1. Generate template & markup

**File**: `templates/core/generate.html`

**Intent**: Replace the two-column select/textarea layout with the handoff's single-column
pill-and-card workspace.

**Contract**: Centred single column (max-width ~1120px). **Template selector**: a
"Template" label row with a "Manage →" link (`template-list`), pill buttons
(`.tmpl-btn`) per template carrying `data-template-id` and `data-generate-title`, a dashed
"+ New template" pill (`template-create`), and a "No templates yet" prompt when empty.
**Modifiers**: one row per option group (right-aligned name + option pills carrying
`data-option-id`, grouped by `data-group-id`); section omitted when no groups. A divider,
then the **workspace**: input state (label, textarea, full-width amber `.k-mono` Generate
button) and a hidden output card (Title — shown only when the template's
`generate_title` is set — and Result, each with a Copy button, plus a full "Copy to
clipboard" button and "← Edit text" / "↻ Regenerate" controls). An error bar above the
Generate button.

#### 2. Generate page JS

**File**: `templates/core/generate.html` (inline script)

**Intent**: Drive the input → loading → output state machine while preserving the network
contract and safeguards from the current implementation.

**Contract**: Reworked vanilla JS that (a) toggles template pills (single active,
`template_id` source of truth) and reads `?template=` on load to preselect; (b) toggles
modifier pills with radio-per-group + deselect-on-reclick (port of the current
`.option-group` logic); (c) on Generate, validates non-empty text + a chosen template
(else error bar), then POSTs `{template_id, option_ids, text}` to `{% url 'generate-api' %}`
with the `X-CSRFToken` header and the existing `AbortController` ~65s timeout, showing the
loading state with a randomly rotating quip from the handoff list; (d) on success renders
Title (only if present) + Result into copyable fields via `.value` (never `innerHTML`) and
shows the output card; (e) "← Edit text" restores the input state with the prior text
intact, "↻ Regenerate" re-runs with the same input/selections; (f) maps API errors
(4xx/5xx JSON `error`, timeout, network) to the error bar; (g) keeps the clipboard copy
with the `execCommand` fallback and the single-in-flight guard.

### Success Criteria:

#### Automated Verification:

- Tests pass: `uv run pytest`
- Django check passes: `uv run manage.py check`
- Static files collect cleanly: `uv run manage.py collectstatic --noinput`
- Lint passes: `uv run ruff check .`
- Format check passes: `uv run ruff format --check .`

#### Manual Verification:

- Selecting template pills and modifier pills behaves (single-select per group, reclick
  deselects); `?template=pk` from the Templates list preselects the right pill.
- Generate shows the loading state with rotating quips, then the output card; Title shows
  only for templates with `generate_title`.
- "Edit text" returns to the input with text preserved; "Regenerate" reruns.
- Copy buttons (per-field and full) copy and flash "Copied!".
- Error states surface in the bar: empty text, no template, and API 400/429/502/timeout.
- Empty-state prompt shows when the user has no templates.

**Implementation Note**: After completing this phase and all automated verification
passes, pause for manual confirmation. This is the final phase.

---

## Testing Strategy

### Unit Tests:

- A new view test: a POST to `template-delete` / `option-group-delete` for an owned object
  deletes it and returns `204`; a foreign/missing pk returns `404`.
- Keep the existing `tests/test_core_models.py` green.

### Integration Tests:

- Existing `generate_api` behaviour is unchanged; rely on its current coverage and the
  manual generate walkthrough. No contract change to test.

### Manual Testing Steps:

1. Run `uv run manage.py runserver`; load each screen logged out and in.
2. Drive the screens with `playwright-cli` (now available) against `runserver` —
   screenshot each to compare against the `design_handoff/` prototypes:
   `playwright-cli open http://127.0.0.1:8000/` then `goto`/`screenshot` per page.
3. Exercise: login modal + failed login page; template & modifier CRUD; formset
   add/delete + validation; delete dialog (fade-out, 204); full generate flow incl.
   Edit/Regenerate, copy, and each error path.

## Performance Considerations

Negligible — static CSS + fonts from CDN, no added JS frameworks, SSR unchanged. The
manifest-storage `collectstatic` step already exists in the Docker build; the only delta
is one more stylesheet to hash.

## Migration Notes

No data migration. Deployment note: the new `static/css/korpotron.css` is picked up by the
existing Dockerfile `collectstatic` stage once `STATICFILES_DIRS` is set — verify the
Docker build before merging (per `context/foundation/lessons.md`).

## References

- Research: `context/changes/ui-refresh/research.md`
- Design handoff + tokens/specs: `context/changes/ui-refresh/design_handoff/README.md`
- Decision record: `context/changes/ui-refresh/change.md`
- Generate contract: `core/views.py:146` (`generate_api`); URL name `generate-api`
  (`core/urls.py:18`)
- Formset JS pattern to preserve: `templates/core/optiongroup_form.html:64-96`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands.
> Do not rename step titles.

### Phase 1: Design system foundation & app shell

#### Automated

- [x] 1.1 Django check passes: `uv run manage.py check` — 65c232c
- [x] 1.2 Static files collect cleanly: `uv run manage.py collectstatic --noinput` — 65c232c
- [x] 1.3 Lint passes: `uv run ruff check .` — 65c232c
- [x] 1.4 Format check passes: `uv run ruff format --check .` — 65c232c
- [x] 1.5 Existing tests pass: `uv run pytest` — 65c232c

#### Manual

- [x] 1.6 Authenticated pages render with frosted nav, IBM Plex fonts, new background; brand `KORPOTRON™`, third nav item "Modifiers" — 65c232c
- [x] 1.7 No console errors; `korpotron.css` and fonts load on `runserver` — 65c232c
- [x] 1.8 Nav active/hover states behave per the design — 65c232c

### Phase 2: Landing page & login

#### Automated

- [x] 2.1 Django check passes: `uv run manage.py check` — aa216cf
- [x] 2.2 Templates render without errors (smoke): `uv run pytest` — aa216cf
- [x] 2.3 Lint passes: `uv run ruff check .` — aa216cf

#### Manual

- [x] 2.4 Anonymous `/` shows new landing; both "Log in" triggers link to the standalone login page (modal removed per user request — single login form) — aa216cf
- [x] 2.5 Valid login redirects to generate; invalid login shows standalone page with error bar — aa216cf
- [x] 2.6 Protected URL while logged out redirects to the designed standalone login — aa216cf
- [x] 2.7 Landing and login match the prototypes — aa216cf

### Phase 3: Lists, forms & delete flow

#### Automated

- [x] 3.1 Existing + new tests pass: `uv run pytest` (incl. delete → 204 test)
- [x] 3.2 Django check passes: `uv run manage.py check`
- [x] 3.3 Lint passes: `uv run ruff check .`
- [x] 3.4 Format check passes: `uv run ruff format --check .`

#### Manual

- [x] 3.5 Template create/edit works; `generate_title` toggle reflects and saves state
- [x] 3.6 Modifier create/edit works; option rows add/delete; zero-option + duplicate-name errors show
- [x] 3.7 Delete dialog opens with right name, deletes on confirm (row fades, no reload), cancels/backdrop-closes — both lists
- [x] 3.8 Empty states render for both lists

### Phase 4: Generate workspace

#### Automated

- [x] 4.1 Tests pass: `uv run pytest`
- [x] 4.2 Django check passes: `uv run manage.py check`
- [x] 4.3 Static files collect cleanly: `uv run manage.py collectstatic --noinput`
- [x] 4.4 Lint passes: `uv run ruff check .`
- [x] 4.5 Format check passes: `uv run ruff format --check .`

#### Manual

- [x] 4.6 Template + modifier pills behave (single-select per group, reclick deselects); `?template=pk` preselects
- [x] 4.7 Generate shows loading quips then output card; Title only for `generate_title` templates
- [x] 4.8 "Edit text" preserves text; "Regenerate" reruns
- [x] 4.9 Copy buttons (per-field + full) copy and flash "Copied!"
- [x] 4.10 Error states surface: empty text, no template, API 400/429/502/timeout
- [x] 4.11 Empty-state prompt shows when the user has no templates
