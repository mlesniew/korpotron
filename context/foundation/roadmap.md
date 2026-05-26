---
project: "Korpotron"
version: 1
status: draft
created: 2026-05-26
updated: 2026-05-26
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
| F-01 | auth-scaffold           | (foundation) log in/out with email+password; all app views protected              | —                      | Access Control                                  | ready    |
| F-02 | core-data-model         | (foundation) Template, OptionGroup, Option models exist with user ownership       | —                      | FR-001, FR-004                                  | ready    |
| S-01 | template-management     | create, view, edit, and delete templates                                          | F-01, F-02             | FR-001, FR-002, FR-003                          | proposed |
| S-02 | option-group-management | create, view, edit, and delete option groups with their options                   | F-01, F-02             | FR-004, FR-005, FR-006                          | proposed |
| S-03 | text-generation-flow    | select a template, pick options, enter text, generate result, copy to clipboard   | F-01, F-02, S-01, S-02 | FR-007, FR-008, FR-009, FR-011, FR-012, US-01   | blocked  |

## Streams

Navigation aid — groups items that share a Prerequisites chain. Canonical ordering still lives in the dependency graph below; this table is the proposed reading order across parallel tracks.

| Stream | Theme                                | Chain                              | Note                                                                                     |
|--------|--------------------------------------|------------------------------------|------------------------------------------------------------------------------------------|
| A      | Foundations → Template management → Generation | `F-01` / `F-02` → `S-01` → `S-03` | F-01 and F-02 run in parallel; S-03 also requires S-02 from Stream B.                  |
| B      | Option group management              | `S-02`                             | Branches from F-01+F-02 (parallel with S-01); converges at S-03 via shared prerequisites.|

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
- **Status:** ready

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
- **Status:** ready

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
- **Status:** proposed

### S-02: Option group management

- **Outcome:** user can create, view, edit, and delete option groups, each with one or more named options carrying instruction text.
- **Change ID:** option-group-management
- **PRD refs:** FR-004, FR-005, FR-006
- **Prerequisites:** F-01 (login_required), F-02 (OptionGroup + Option models)
- **Parallel with:** S-01
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Nested options (one OptionGroup contains multiple Options) need careful form handling; the mutual-exclusivity invariant is enforced by the data model, not the UI, so the UI just needs to display and save correctly.
- **Status:** proposed

### S-03: Text generation flow

- **Outcome:** user can select a template, optionally select one option per group, enter text to transform, trigger generation, see the verbatim result, and copy it to the clipboard.
- **Change ID:** text-generation-flow
- **PRD refs:** FR-007, FR-008, FR-009, FR-011, FR-012, US-01
- **Prerequisites:** F-01, F-02, S-01 (templates exist to select), S-02 (option groups exist to pick from)
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - Which LLM / text-generation service will be used? — Owner: user. Block: yes.
- **Risk:** LLM integration is the riskiest element (external API, key management, latency); blocked until the provider is decided. The input non-retention NFR (no storing user input after request completes) must be explicitly verified in implementation.
- **Status:** blocked

## Backlog Handoff

| Roadmap ID | Change ID               | Suggested issue title                                      | Ready for `/10x-plan` | Notes                                    |
|------------|-------------------------|------------------------------------------------------------|-----------------------|------------------------------------------|
| F-01       | auth-scaffold           | Add login/logout views and protect all app routes          | yes                   | Run `/10x-plan auth-scaffold`            |
| F-02       | core-data-model         | Define Template, OptionGroup, Option models and migrations | yes                   | Run `/10x-plan core-data-model`; run parallel with F-01 |
| S-01       | template-management     | Build template CRUD views                                  | no                    | Needs F-01, F-02 done first              |
| S-02       | option-group-management | Build option group CRUD with nested options                | no                    | Needs F-01, F-02; run parallel with S-01 |
| S-03       | text-generation-flow    | Wire LLM call, prompt assembly, result display, clipboard copy | no                | Blocked: LLM provider decision needed first |

## Open Roadmap Questions

1. **Which text-generation service / LLM provider will be used?** — Owner: user. Block: yes — gates S-03 (`text-generation-flow`). Resolve before planning S-03.
2. **Confirm target_scale assumptions** (`qps: low`, `data_volume: small`) — Owner: user. Block: no — inferred for single-digit users; correct if traffic expectations change.
3. **Confirm revised clipboard copy acceptance criteria** — one-click copy preferred; pre-selected text box is acceptable fallback (per FR-012 Socratic note in PRD). Owner: user. Block: no — confirm before S-03 implementation.

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

(Empty on first generation. `/10x-archive` appends entries here when a change is archived.)
