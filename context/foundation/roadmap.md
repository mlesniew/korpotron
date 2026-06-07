---
project: "Korpotron"
version: 1
status: active
created: 2026-05-26
updated: 2026-06-07
prd_version: 1
main_goal: speed
top_blocker: decisions
---

# Roadmap: Korpotron

> Derived from `context/foundation/prd.md` (v1) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Vision recap

Knowledge workers who repeatedly paste stored prompts into LLM chat tools to polish short-form text lose 2-3 minutes per rewrite to copy-paste friction. Korpotron removes that friction: a minimal, opinionated web app where the user selects a saved template, optionally picks tone/style options, pastes their text, and copies the result — all without leaving the app.

## North star

**S-03: text generation flow** — the smallest end-to-end slice that proves whether stored templates + LLM integration reduces text-rewrite time from minutes to seconds; the core hypothesis — that a purpose-built template + LLM flow eliminates the copy-paste chore — is confirmed when this slice ships and the primary success criterion (full flow under 60 s) is met.

> "North star" here means the one slice whose successful delivery proves the product hypothesis — placed as early as prerequisites allow, because everything else only matters if this works.

## At a glance

| ID   | Change ID               | Outcome (user can …)                                                              | Prerequisites          | PRD refs                                        | Status   |
|------|-------------------------|-----------------------------------------------------------------------------------|------------------------|-------------------------------------------------|----------|
| F-01 | auth-scaffold           | (foundation) log in/out with email+password; all app views protected              | —                      | Access Control                                  | done    |
| F-02 | core-data-model         | (foundation) Template, OptionGroup, Option models exist with user ownership       | —                      | FR-001, FR-004                                  | done    |
| S-01 | template-management     | create, view, edit, and delete templates                                          | F-01, F-02             | FR-001, FR-002, FR-003                          | done |
| S-02 | option-group-management | create, view, edit, and delete option groups with their options                   | F-01, F-02             | FR-004, FR-005, FR-006                          | done |
| S-03 | text-generation-flow    | select a template, pick options, enter text, generate result, copy to clipboard   | F-01, F-02, S-01, S-02 | FR-007, FR-008, FR-009, FR-011, FR-012, US-01   | done |
| S-04 | landing-page            | unauthenticated visitors see a branded landing page with a "Get started" CTA      | F-01                   | —                                               | planned |
| S-05 | daily-generation-limit  | generation is rate-limited per user per day via env var; users see a friendly message when the limit is reached | F-01, F-02, S-03 | —                          | planned |
| S-06 | onboarding-defaults     | new users get 3 default templates and default option groups seeded from a repo JSON fixture on first login      | F-01, F-02, S-01, S-02 | —                     | done |
| S-07 | option-group-edit-ux    | option group edit page shows a collapsible per-option list with inline editing and icon-based delete + confirm  | F-01, S-02             | —                     | planned |
| S-08 | template-list-ux        | template list page shows a name + delete-icon row per template; clicking the name navigates to the edit page    | F-01, S-01             | —                     | planned |
| S-09 | option-group-list-ux    | option group list page shows a name + delete-icon row per group; clicking the name navigates to the edit page   | F-01, S-02             | —                     | planned |
| S-10 | ui-refresh              | all app pages get a modern, non-generic visual style; forms and layout overhauled; framework TBD via research    | S-04–S-09              | —                     | planned |
| S-11 | user-registration       | users can self-register; accounts are inactive until an admin approves them via the Django admin panel           | F-01                   | —                     | planned |

## Streams

Navigation aid — groups items that share a Prerequisites chain. Canonical ordering still lives in the dependency graph below; this table is the proposed reading order across parallel tracks.

**MVP reached at S-03 (2026-06-01).** Streams A and B below delivered the core product. Streams C–E are post-MVP improvements that can be worked in parallel once the MVP foundations are in place.

| Stream | Theme                                          | Chain                                        | Note                                                                                                        |
|--------|------------------------------------------------|----------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| A      | Foundations → Template management → Generation | `F-01` / `F-02` → `S-01` → `S-03`           | F-01 and F-02 run in parallel; S-03 also requires S-02 from Stream B. **MVP complete.**                    |
| B      | Option group management                        | `F-01` / `F-02` → `S-02`                    | Branches from F-01+F-02 (parallel with S-01); converges at S-03 via shared prerequisites. **MVP complete.**|
| C      | Cost control & onboarding                      | `S-05`, `S-06`                               | Independent of each other; both require MVP foundations. S-05 limits daily generation cost; S-06 seeds new users with useful defaults. |
| D      | UX polish — list & edit pages                  | `S-07` → `S-08`, `S-09`                     | S-07 establishes the icon/confirm-dialog pattern; S-08 and S-09 apply it to template and option group lists. S-08 and S-09 are parallel. |
| E      | Discovery & entry point                        | `S-04`                                       | Standalone; no dependencies on C or D. Adds a public landing page for unauthenticated visitors.             |
| F      | Visual refresh                                 | `S-10`                                       | Sequenced after all other post-MVP slices so structural HTML is stable before the visual layer is applied. Framework choice requires research before planning. |

## Baseline

What's already in place in the codebase as of 2026-05-26 (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend:** absent — no templates, no JS framework; Django TEMPLATES dirs are empty
- **Backend / API:** partial — Django 6.0.5 installed; only admin route in urls.py, no app views
- **Data:** partial — Django ORM + dj-database-url configured, SQLite in dev; no custom models or migrations
- **Auth:** partial — django.contrib.auth in INSTALLED_APPS/middleware; no app-facing login views, login_required, or OAuth flows
- **Deploy / infra:** present — Dockerfile, fly.toml, .github/workflows/deploy.yml all present
- **Observability:** absent — Django defaults only, no Sentry / logging lib / APM

## Foundations

### F-01: Auth scaffold

- **Outcome:** (foundation) Users can log in and out with email + password; all app views are protected with login_required; a login template exists.
- **Change ID:** auth-scaffold
- **PRD refs:** Access Control section (login required; email + password; flat user model)
- **Unlocks:** S-01, S-02, S-03 (all require an authenticated user)
- **Prerequisites:** —
- **Parallel with:** F-02
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Every slice depends on this; sequenced first. Django's built-in auth reduces this to configuration + templates rather than novel code.
- **Status:** done

### F-02: Core data model

- **Outcome:** (foundation) Template, OptionGroup, and Option models exist with migrations applied; each Template and OptionGroup is owned by a User via FK.
- **Change ID:** core-data-model
- **PRD refs:** FR-001 (template fields: name, base prompt, generate-title flag, is-response flag), FR-004 (option group + options structure)
- **Unlocks:** S-01 (Template model), S-02 (OptionGroup/Option models), S-03 (generation reads both)
- **Prerequisites:** —
- **Parallel with:** F-01
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Getting the schema right here avoids migration churn later; S-01, S-02, and S-03 all depend on it.
- **Status:** done

## Slices

### S-01: Template management

- **Outcome:** user can create, view, edit, and delete templates (name, base prompt, generate-title flag, is-response flag).
- **Change ID:** template-management
- **PRD refs:** FR-001, FR-002, FR-003
- **Prerequisites:** F-01 (login_required on all views), F-02 (Template model)
- **Parallel with:** S-02
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Straightforward Django CRUD; must complete before S-03 so at least one template exists for generation testing.
- **Status:** done

### S-02: Option group management

- **Outcome:** user can create, view, edit, and delete option groups, each with one or more named options carrying instruction text.
- **Change ID:** option-group-management
- **PRD refs:** FR-004, FR-005, FR-006
- **Prerequisites:** F-01 (login_required), F-02 (OptionGroup + Option models)
- **Parallel with:** S-01
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Nested options (one OptionGroup contains multiple Options) need careful form handling; the mutual-exclusivity invariant is enforced by the data model, not the UI, so the UI just needs to display and save correctly.
- **Status:** done

### S-03: Text generation flow

- **Outcome:** user can select a template, optionally select one option per group, enter text to transform, trigger generation, see the verbatim result, and copy it to the clipboard.
- **Change ID:** text-generation-flow
- **PRD refs:** FR-007, FR-008, FR-009, FR-011, FR-012, US-01
- **Prerequisites:** F-01, F-02, S-01 (templates exist to select), S-02 (option groups exist to pick from)
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - ~~Which LLM / text-generation service will be used?~~ **Resolved 2026-06-01:** OpenRouter via `openai` SDK — see ADR 001.
- **Risk:** LLM integration is the riskiest element (external API, key management, latency). The input non-retention NFR (no storing user input after request completes) must be explicitly verified in implementation.
- **Status:** done

### S-04: Landing page

- **Outcome:** unauthenticated visitors land on a branded page showing the Korpotron name, a short catchy description, and a "Get started" button that leads to the login form. Authenticated users bypass the landing page and go directly to the app, unchanged.
- **Change ID:** landing-page
- **PRD refs:** —
- **Prerequisites:** F-01 (auth, to detect login state and redirect authenticated users past the page)
- **Parallel with:** S-05, S-06, S-07, S-08, S-09
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Low — pure front-end addition with no data model changes; only affects the unauthenticated entry point.
- **Status:** planned

### S-05: Daily generation limit

- **Outcome:** generation is rate-limited per user per day. The limit is set via a `DAILY_GENERATION_LIMIT` env var (default: `100`; `0` = unlimited). When a user hits the limit they see a friendly message on the generation page telling them to come back in a few hours or tomorrow. No remaining count or reset time is displayed.
- **Change ID:** daily-generation-limit
- **PRD refs:** —
- **Prerequisites:** F-01 (per-user identity), F-02 (data model for counter storage), S-03 (generation flow to enforce the limit)
- **Parallel with:** S-04, S-06, S-07, S-08, S-09
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Low — accuracy is explicitly not required; a per-user counter reset at midnight UTC is sufficient. Env var default of 100 keeps runaway costs in check.
- **Status:** planned

### S-06: Onboarding defaults

- **Outcome:** new users have 3 default templates and a set of default option groups seeded into their personal data on first login. The defaults are owned by the user and fully editable and deletable. Content is defined in a JSON fixture file stored in the repository.
- **Change ID:** onboarding-defaults
- **PRD refs:** —
- **Prerequisites:** F-01 (login signal to trigger seeding), F-02 (Template, OptionGroup, Option models), S-01 (template data shape), S-02 (option group data shape)
- **Parallel with:** S-04, S-05, S-07, S-08, S-09
- **Blockers:** —
- **Unknowns:** —
- **Notes:**
  - Trigger: on login, if the user has zero templates **and** zero option groups, seed from the fixture (simple enough; no separate first-login flag needed).
  - Default templates (to be authored during planning): corporate email, Teams/IM message, peer feedback — all oriented toward corporate communication.
  - Default option groups: Language (English, Polish, German), Tone, Corporate Buzzword level (controls how heavily corporate jargon is applied).
  - Exact prompt text for templates and options is defined during the planning phase.
- **Risk:** Low — seeding is a one-time write at login; idempotency guard (zero templates + zero option groups) prevents double-seeding. JSON fixture keeps content auditable and easy to update without code changes.
- **Status:** done

### S-07: Option group edit UX

- **Outcome:** the option group edit page is redesigned for clarity. The page shows the group title (editable) and a collapsed list of its options. Each row shows the option name and a delete icon (MDI or similar, already in the project). Clicking a row expands it inline to reveal editable title and instructions fields plus a Save button; saving collapses the row. Clicking the delete icon shows a confirmation dialog; confirming deletes the option. No full-page reloads for individual option edits or deletes.
- **Change ID:** option-group-edit-ux
- **PRD refs:** —
- **Prerequisites:** F-01 (auth), S-02 (option group management to build upon)
- **Parallel with:** S-04, S-05, S-06
- **Blockers:** —
- **Unknowns:** —
- **Notes:**
  - Vanilla JS only — no new JS libraries or build steps introduced.
  - Backed by lightweight JSON CRUD endpoints for individual option create / update / delete.
  - Icon set: MDI icons (or equivalent already present in the project).
- **Risk:** Low-medium — introduces JS and REST endpoints for the first time; keeping JS vanilla and scoped to this page limits blast radius.
- **Status:** planned

### S-08: Template list UX

- **Outcome:** the template list page is redesigned for consistency with S-07. Each template is shown as a row with its name on the left and a delete icon button on the right. Clicking the delete icon shows the same confirmation dialog as S-07; confirming deletes the template. Clicking the template name navigates to the existing edit page (no inline editing on the list).
- **Change ID:** template-list-ux
- **PRD refs:** —
- **Prerequisites:** F-01 (auth), S-01 (template management to build upon)
- **Parallel with:** S-04, S-05, S-06, S-07, S-09
- **Blockers:** —
- **Unknowns:** —
- **Notes:**
  - Delete uses the same icon and confirmation pattern established in S-07 for visual consistency.
  - No inline editing — clicking the name navigates to the existing template edit page.
- **Risk:** Low — primarily a template/view change; reuses the delete-with-confirmation pattern from S-07.
- **Status:** planned

### S-09: Option group list UX

- **Outcome:** the option group list page is redesigned for consistency with S-07 and S-08. Each group is shown as a row with its name on the left and a delete icon button on the right. Clicking the delete icon shows a confirmation dialog; confirming deletes the group. Clicking the name navigates to the existing option group edit page.
- **Change ID:** option-group-list-ux
- **PRD refs:** —
- **Prerequisites:** F-01 (auth), S-02 (option group management to build upon)
- **Parallel with:** S-04, S-05, S-06, S-07, S-08
- **Blockers:** —
- **Unknowns:** —
- **Notes:**
  - Delete uses the same icon and confirmation pattern established in S-07.
  - No inline editing — clicking the name navigates to the existing option group edit page.
- **Risk:** Low — primarily a template/view change; reuses the delete-with-confirmation pattern from S-07.
- **Status:** planned

### S-11: User registration

- **Outcome:** users can register themselves via a registration form (username, email, password). Newly created accounts are set to `is_active=False` and cannot log in until an admin approves them. After submitting the form, the user sees a "pending approval" message. Approval is done by the admin in the existing Django admin panel — no new admin UI required. A "Register" link appears on the login page.
- **Change ID:** user-registration
- **PRD refs:** —
- **Prerequisites:** F-01 (auth scaffold — login/logout foundation)
- **Parallel with:** S-05, S-06, S-07, S-08, S-09
- **Blockers:** —
- **Unknowns:** —
- **Notes:**
  - Uses Django's built-in `is_active` flag — no new model fields needed.
  - S-04 (landing page) should also carry a "Register" link once it ships; coordinate during S-04 implementation.
  - No email notifications — admin must check the Django admin panel to discover pending registrations.
- **Risk:** Low — thin view + form on top of Django's existing User model; approval leverages built-in admin.
- **Status:** planned

### S-10: UI refresh

- **Outcome:** all app pages have a modern, cohesive visual style. Forms are no longer rendered with bare Django widgets. The look is fresh and distinct from a default Bootstrap theme, without introducing a SPA or a JS build pipeline. CSS/JS loaded from CDN is acceptable.
- **Change ID:** ui-refresh
- **PRD refs:** —
- **Prerequisites:** S-04, S-05, S-06, S-07, S-08, S-09 — sequenced last so all structural HTML changes from earlier slices are in place before the visual layer is applied, avoiding double-rework.
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - **Which CSS/UI framework or library?** — Must be resolved via research before planning starts. Constraints: CDN-deliverable, SSR-compatible, more distinctive than default Bootstrap, minimal JS build overhead. Examples to evaluate: Tailwind CSS (CDN play), Pico CSS, Bulma, DaisyUI, or a lightweight custom approach.
- **Notes:**
  - Scope is visual only — no functionality changes.
  - Form rendering (currently bare Django widgets) is a priority target.
  - Exact design decisions (colour palette, typography, component style) are deferred to the planning phase, after the framework is chosen.
- **Risk:** Medium — touches every template; a poor framework choice or incomplete rollout leaves the UI inconsistent. Mitigated by sequencing after all structural slices and making the framework decision explicit before implementation begins.
- **Status:** planned

## Implementation Summary

MVP (F-01, F-02, S-01–S-03) shipped and archived as of 2026-06-01. Six post-MVP slices (S-04–S-09) are planned as of 2026-06-04.

| Roadmap ID | Change ID               | Status  | Archived |
|------------|-------------------------|---------|----------|
| F-01       | auth-scaffold           | done    | 2026-05-26 |
| F-02       | core-data-model         | done    | 2026-05-28 |
| S-01       | template-management     | done    | 2026-05-29 |
| S-02       | option-group-management | done    | 2026-05-29 |
| S-03       | text-generation-flow    | done    | 2026-06-01 |
| S-04       | landing-page            | planned | — |
| S-05       | daily-generation-limit  | planned | — |
| S-06       | onboarding-defaults     | planned | — |
| S-07       | option-group-edit-ux    | planned | — |
| S-08       | template-list-ux        | planned | — |
| S-09       | option-group-list-ux    | planned | — |
| S-10       | ui-refresh              | planned | — |
| S-11       | user-registration       | planned | — |

See the `## Done` section below for MVP archive locations.

## Open Roadmap Questions

1. ~~**Which text-generation service / LLM provider will be used?**~~ **Resolved 2026-06-01:** OpenRouter via `openai` SDK (`base_url` override). See `context/foundation/adr/001-llm-provider-openrouter.md`.
2. **Confirm target_scale assumptions** (`qps: low`, `data_volume: small`) — Owner: user. Block: no — inferred for single-digit users; correct if traffic expectations change.
3. ~~**Confirm revised clipboard copy acceptance criteria**~~ **Resolved 2026-06-01:** S-03 shipped; one-click copy implemented.

## Parked

- **is-response / reply-context input (FR-010)** — Why parked: nice-to-have per PRD; demoted in Socratic review; deferred to v2.
- **OAuth / social login** — Why parked: email + password sufficient for MVP; PRD names OAuth as an option but `speed` goal defers it until the core flow ships.
- **Observability (Sentry / APM)** — Why parked: small scale, solo project, `speed` goal; add if runtime issues surface post-MVP.
- **No mobile / mobile-first experience** — Why parked: PRD Non-Goal; desktop-only for MVP.
- **No external integrations** — Why parked: PRD Non-Goal; no email clients, Jira, Slack, etc.
- **No multi-user workspaces or sharing** — Why parked: PRD Non-Goal.
- **No import/export of templates or option groups** — Why parked: PRD Non-Goal.
- **No history or audit log** — Why parked: PRD Non-Goal.
- **No automation or scheduling** — Why parked: PRD Non-Goal.
- **No prompt editing during normal use** — Why parked: PRD Non-Goal.

## Done

- **(foundation) F-01: log in/out with email+password; all app views protected** — Archived 2026-06-01 → `context/archive/2026-05-26-auth-scaffold/`. Lesson: —.
- **(foundation) F-02: Template, OptionGroup, Option models exist with user ownership** — Archived 2026-06-01 → `context/archive/2026-05-28-core-data-model/`. Lesson: —.
- **S-01: create, view, edit, and delete templates** — Archived 2026-06-01 → `context/archive/2026-05-29-template-management/`. Lesson: —.
- **S-02: create, view, edit, and delete option groups with their options** — Archived 2026-06-01 → `context/archive/2026-05-29-option-group-management/`. Lesson: —.
- **S-03: user can select a template, optionally select one option per group, enter text to transform, trigger generation, see the verbatim result, and copy it to the clipboard.** — Archived 2026-06-01 → `context/archive/2026-06-01-text-generation-flow/`. Lesson: —.
- **S-06: new users get 3 default templates and default option groups seeded from a repo JSON fixture on first login** — Archived 2026-06-07 → `context/archive/2026-06-05-onboarding-defaults/`. Lesson: —.
