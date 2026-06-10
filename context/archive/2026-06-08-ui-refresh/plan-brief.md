# UI Refresh — Plan Brief

> Full plan: `context/changes/ui-refresh/plan.md` Research: `context/changes/ui-refresh/research.md` Design handoff:
> `context/changes/ui-refresh/design_handoff/README.md`

## What & Why

The current UI is generic, unstyled Bootstrap. This change recreates seven high-fidelity design prototypes
(`design_handoff/`) as the app's Django templates, giving Korpotron a distinctive, purpose-built look — while **keeping
raw Bootstrap 5** and adding a bespoke design system on top (no framework swap, no build step, no architectural change).

## Starting Point

A small Django SSR app on Bootstrap 5.3.3 (CDN), with **no project CSS file**, inline Bootstrap classes everywhere,
`{{ form.as_p }}` forms, and hand-written vanilla JS on the generate and modifier-form pages. WhiteNoise + manifest
static storage and a Dockerfile `collectstatic` step are already in place.

## Desired End State

All seven screens match the prototypes pixel-closely: a frosted-glass nav with a `KORPOTRON™` mono brand, a dark landing
hero with a login modal, a designed standalone login page, card-based Templates/Modifiers lists with a JS delete dialog,
bespoke forms (toggle switch, two-column formset grid), and a single-column generate workspace that transitions input →
loading (rotating quips) → output with Edit/Regenerate. Styling lives in one new `static/css/korpotron.css`; behaviour
and the `generate-api` contract are unchanged.

## Key Decisions Made

| Decision             | Choice                                                       | Why                                                                        | Source            |
| -------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------- | ----------------- |
| CSS strategy         | Raw Bootstrap 5 + custom `korpotron.css`                     | Distinctive design exists; no framework swap needed                        | Frame (change.md) |
| Complexity / phasing | MEDIUM, 4 phases                                             | Broad but architecturally shallow; no model changes                        | Plan              |
| Failed-login UX      | Falls through to designed standalone login page              | Page now renders `form.errors`; default Django behaviour, zero view wiring | Plan              |
| Generate workspace   | Full stateful input→loading→output, Edit/Regenerate          | Matches the handoff; best UX                                               | Plan              |
| Delete flow          | JS dialog `fetch()`-POSTs → view returns **204** → row fades | JS assumed; no GET confirm pages needed                                    | Plan              |
| Static location      | `static/css/korpotron.css` + `STATICFILES_DIRS`              | Matches handoff path; collected under manifest storage                     | Plan              |
| "Use →" deep link    | Handled in JS (`?template=`)                                 | `HomeView` ignores query params; no backend change                         | Plan              |

## Scope

**In scope:** all 7 screens (landing, login, generate, template list/form, modifier list/form); `korpotron.css` design
system; frosted nav + "Option Groups → Modifiers" label rename; bespoke forms; JS delete dialog with DeleteView → 204;
generate state machine.

**Out of scope:** CSS framework swap; data-model/migration changes; `generate-api` contract changes;
crispy-forms/widget-tweaks; URL/model renames; no-JS delete fallback; dark mode/theming.

## Architecture / Approach

Build the shared substrate first, then screens in increasing risk order. A new `static/css/korpotron.css` holds tokens +
custom component classes; a `_head.html` partial centralises the Bootstrap/fonts/CSS links for `base.html` and the two
anonymous pages. Templates use Bootstrap grid/utilities + `k-*` classes. JS stays vanilla and inline, except a shared
`_delete_dialog.html` include. The only backend change: two DeleteViews return `204` instead of redirecting.

## Phases at a Glance

| Phase                    | What it delivers                                                     | Key risk                                                     |
| ------------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------ |
| 1. Foundation & shell    | `korpotron.css`, fonts, `STATICFILES_DIRS`, frosted nav, shared head | Manifest `collectstatic` / `{% static %}` refs must resolve  |
| 2. Landing + login       | Dark hero + login modal; designed standalone login page              | Modal open/close + failed-login fall-through correctness     |
| 3. Lists, forms & delete | Card lists, bespoke forms, JS delete dialog, DeleteView→204          | Formset add/delete mechanics; CSRF on fetch delete           |
| 4. Generate workspace    | Pill selectors + stateful input→loading→output, Edit/Regenerate      | Largest JS rework; preserve fetch/timeout/clipboard contract |

**Prerequisites:** none beyond the existing dev setup (`uv run manage.py runserver`); `playwright-cli` available for
visual verification. **Estimated effort:** ~4 sessions, one per phase; Phase 4 is the heaviest.

## Open Risks & Assumptions

- Assumes JS is always enabled (no no-JS delete path; GET confirm pages removed).
- `{% static %}` refs must survive manifest `collectstatic` — verify the Docker build before merge (per `lessons.md`).
- Generate JS rework must preserve the existing safeguards (single in-flight request, `AbortController` timeout,
  clipboard fallback, `.value`-not-`innerHTML` rendering).

## Success Criteria (Summary)

- Every screen matches its `design_handoff/` prototype and all interactions work (login modal, delete dialog, formset,
  generate state machine).
- `pytest`, `ruff check`, `ruff format --check`, `manage.py check`, and `collectstatic` all pass; the Docker build
  succeeds.
- No change in generate behaviour or any URL/model names.
