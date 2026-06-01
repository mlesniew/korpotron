---
project: "Korpotron"
version: 1
status: implemented
created: 2026-05-21
completed: 2026-06-01
context_type: greenfield
product_type: web-app
target_scale:
  users: small
  qps: low
  data_volume: small
timeline_budget:
  mvp_weeks: 2
  hard_deadline: null
  after_hours_only: true
---

## Vision & Problem Statement

Knowledge workers who regularly use LLMs to polish short-form text — emails, comments, documentation — store their reusable prompts in plain text files. Every use requires opening that file, copying the prompt into a chat tool, adjusting it for tone or context, and then copying the result back. This turns a 30-second text improvement into a 3-minute chore.

The insight: prompt-management tools exist but they are designed for developers and power users, not for someone who just wants to rewrite an email quickly. The gap is a purpose-built tool that is minimal, fast, and opinionated about the workflow — not a general-purpose prompt library.

## Status: Implemented

**Completed 2026-06-01.** All primary and secondary success criteria met:
- ✓ Logged-in user can select template, optionally pick options, enter text, generate result, copy to clipboard — all without leaving the app
- ✓ Full flow completes under 60 seconds
- ✓ Input text is not persisted or logged beyond the request scope
- ✓ Usable on desktop via Django web app, no installs required
- ✓ Template and option group configuration persists reliably

See `context/foundation/roadmap.md` for implementation summary and archived change folders.

## User & Persona

**Primary persona**: a solo knowledge worker (the author) who writes emails, documentation, and comments daily and uses LLMs to polish them. They already know what kind of output they want (the right tone, the right format) but have accumulated a set of prompts that work — and want to apply those prompts with the minimum number of steps. They are technically capable but do not want to manage a developer tool. They reach for this product every time they are about to paste a prompt into a general-purpose LLM chat tool from a text file.

## Success Criteria

### Primary
- A logged-in user can select a template, optionally pick options, enter text, generate the result, and copy it to the clipboard — all without leaving the app.

### Secondary
- The complete flow (open app → copy result) takes under 60 seconds.

### Guardrails
- Input text submitted for transformation is not stored or logged beyond the scope of the request.
- The app is usable on a standard desktop browser with no installs or extensions — open a URL and use it.
- Template and option group configuration persists reliably; no silent data loss.

## User Stories

### US-01: Transform text using a template

- **Given** a logged-in user with at least one template configured
- **When** they select a template, optionally pick options from option groups, enter their text, and click Generate
- **Then** they see the rewritten result and can copy it to the clipboard

#### Acceptance Criteria
- Result is displayed verbatim — no silent truncation or modification
- Clipboard copy is available without manually selecting result text; a pre-selected text box is an acceptable fallback if the one-click clipboard action is unavailable
- The original-message input is only shown when the selected template has the is-response flag set (see FR-010, nice-to-have)

## Functional Requirements

### Template management
- FR-001: User can create a template with a name, base prompt, generate-title flag, and is-response flag. Priority: must-have
  > Socrates: Counter-argument considered: "A personal tool could load templates from a config file instead of building a management UI." Resolution: kept. The product's value is in making prompt management fast and accessible — requiring config-file edits reintroduces the friction the tool is meant to remove.
- FR-002: User can edit an existing template. Priority: must-have
  > Socrates: Stands with FR-001.
- FR-003: User can delete a template. Priority: must-have
  > Socrates: Stands with FR-001.

### Option group management
- FR-004: User can create an option group with a name and a set of named options (each with instruction text). Priority: must-have
  > Socrates: Counter-argument considered: "A simpler approach — a free-text 'extra instructions' field per run — delivers the same value with less setup." Resolution: kept. Option groups enforce mutual exclusivity within a group (e.g. Formal vs Casual under Tone). Without groups, conflicting instructions can be selected simultaneously, producing incoherent output. Putting conflict-avoidance responsibility on the user at generation time defeats the speed goal. Groups are a load-bearing design choice, not a nice-to-have.
- FR-005: User can edit an existing option group. Priority: must-have
  > Socrates: Stands with FR-004.
- FR-006: User can delete an option group. Priority: must-have
  > Socrates: Stands with FR-004.

### Core workflow
- FR-007: User can select a template to use for a transformation. Priority: must-have
  > Socrates: No counter-argument; stands as written.
- FR-008: User can select zero or more options from any option groups before transforming. Priority: must-have
  > Socrates: No counter-argument; stands as written.
- FR-009: User can enter the text to transform. Priority: must-have
  > Socrates: No counter-argument; stands as written.
- FR-010: User can enter the original message when the selected template has the is-response flag set. Priority: nice-to-have
  > Socrates: Counter-argument considered: "If replying to messages is rare, is-response adds complexity for marginal gain." Resolution: demoted to nice-to-have. The reply use case is real but not frequent enough to block MVP. The is-response flag and its input field can land in v2.
- FR-011: User can trigger generation and see the rewritten result. Priority: must-have
  > Socrates: No counter-argument; stands as written.
- FR-012: User can copy the generated result to the clipboard. Priority: must-have
  > Socrates: Counter-argument considered: "Browser clipboard APIs are unreliable across HTTP/HTTPS and focus states — a one-click button may silently fail." Resolution: revised. A pre-selected text box (select-all + Ctrl+C) is an acceptable fallback for MVP. One-click copy is preferred but not a hard requirement if the API is not available.

## Non-Functional Requirements

- Input text submitted for transformation leaves no trace in operator-accessible storage after the request that consumed it completes.
- The product is usable on the current major versions of mainstream desktop browsers without installation or extensions.
- Template and option group configuration survives browser restarts and device changes — no silent loss of user-created data.

## Business Logic

The app assembles a prompt from a template's base instruction and the injected text from any selected option group choices, then submits the composite for text generation to produce a rewritten version of the user's input.

Option groups are structured so that only one option per group can be active at a time. This guarantees that the assembled prompt contains no conflicting instructions — the composition rule is enforced by the option group structure, not by the user at generation time. The user selects at most one option per group, and the app merges the selected instruction texts into the base prompt before submitting it for text generation.

The output is displayed verbatim to the user for review and copying.

## Access Control

Login required. Users authenticate via email + password or OAuth. Flat model — every logged-in user has full access to create, edit, and use templates and option groups. No role separation in the MVP.

## Non-Goals

- **No mobile or mobile-first experience** — the app is optimised for desktop browsers; mobile layout is not in scope for the MVP.
- **No integrations with external systems** — no email clients, Jira, Teams, Slack, or similar; input and output stay inside the app.
- **No multi-user workspaces or sharing** — templates and option groups are per-user; no shared libraries or team accounts.
- **No import/export of templates or option groups** — configuration is created in-app; no bulk transfer in or out.
- **No history or audit log** — once the result is copied, it is gone; no session replay or history view.
- **No automation or scheduling** — the tool is triggered manually each time; no batch processing or recurring runs.
- **No prompt editing during normal use** — users select a template and options; they do not edit the raw prompt mid-workflow.
- **is-response / reply-context input deferred to v2** — the template is-response flag and its associated original-message input field are captured as FR-010 (nice-to-have) and are out of MVP scope.

## Open Questions

1. **`target_scale.qps` and `target_scale.data_volume`** — inferred as `low` / `small` based on single-digit user count. Confirm or correct before tech-stack selection if the anticipated traffic or data profile is different.
2. **Which text-generation service will be used** — not captured in this PRD by design; resolve during tech-stack selection. Owner: user.
3. **US-01 acceptance criteria vs FR-012** — the original acceptance criteria stated one-click copy; the Socratic review of FR-012 revised this to allow a pre-selected text box as a fallback. US-01 has been updated accordingly. Confirm the revised wording is acceptable before implementation.
