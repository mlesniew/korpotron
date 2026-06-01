# Text Generation Flow — Plan Brief

> Full plan: `context/changes/text-generation-flow/plan.md`

## What & Why

S-03 is Korpotron's north-star slice: the smallest end-to-end flow that proves the product hypothesis — that a purpose-built template + LLM flow eliminates the copy-paste chore. The user selects a saved template, optionally picks tone/style options, pastes text, generates a rewrite, and copies the result — all on one screen, under 60 seconds.

## Starting Point

Auth, the `Template`/`OptionGroup`/`Option` models, and the template + option-group CRUD (S-01, S-02) are all built. The provider is decided (OpenRouter via the `openai` SDK, ADR 001) but `openai` isn't installed yet. The home page at `/` is a placeholder. No generation code exists.

## Desired End State

Visiting `/` shows one screen: a template picker, a text box, button groups (one per option group) beneath it, and a Generate button. Generating shows a spinner, then a copyable body — and a copyable title when the template's `generate_title` is on. Errors show inline without losing input. No input or output is ever persisted or logged.

## Key Decisions Made

| Decision                  | Choice                                                        | Why (1 sentence)                                                                 | Source |
| ------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------- | ------ |
| Request/response cycle    | `fetch()` to a JSON endpoint                                 | Preserves selections/input across generation and supports a clean spinner.       | Plan   |
| Loading & error UX        | Spinner + inline dismissible error alert                     | Clear feedback, retry without losing input — fits the speed goal.                | Plan   |
| Entry point               | Replace the placeholder home at `/`                          | Zero-navigation landing on the core action serves the under-60s goal.            | Plan   |
| Option selection UI       | Bootstrap **button groups** below the text box, toggle/deselect | Big targets, fast to scan/click; click-selected-again clears the group.        | Plan (user) |
| Title output              | Separate, independently copyable title + body                | Matches email/Jira/announcement (subject + body) use cases.                      | Plan   |
| Prompt structure          | App-owned system prompt + tagged `<instructions>`/`<content>` user msg | Stable authority + instruction-vs-content boundary defends against injection from pasted content. | Plan (user) |
| Output contract           | **Always** tagged result (`<body>`, `<title>` when requested) | Deterministic parsing, graceful fallback, extensible for future fields.          | Plan (user) |

## Scope

**In scope:** generate screen at `/`; LLM service layer (prompt assembly + OpenRouter call + tagged parsing); JSON generate endpoint with ownership + one-per-group validation; copyable title/body; spinner + inline errors; full test coverage incl. non-retention; **documentation updates** (`.env.example`, `CLAUDE.md`, `deployment-steps.md`, and an `infrastructure.md` consistency check) for the new OpenRouter env vars/secrets.

**Out of scope:** reply/original-message input (`is_response`, v2); generation history/persistence/logging; streaming; new frontend deps; any template/option CRUD or model/migration changes.

## Architecture / Approach

Three bottom-up layers: **(1)** `core/llm.py` — pure functions for message assembly (app-owned system prompt + delimited user message) and tagged-result parsing, plus a patchable OpenRouter client factory. **(2)** `GenerateView` (GET, replaces home) + a `generate` JSON endpoint (POST) that validates user-owned template/options and the one-per-group invariant, calls the service, returns `{title, body}` or a structured error — no DB writes. **(3)** `templates/core/generate.html` with inline vanilla JS for button-group toggling, the fetch call, spinner, result rendering, and clipboard copy.

## Phases at a Glance

| Phase                       | What it delivers                                              | Key risk                                                        |
| --------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------- |
| 1. LLM service layer        | `openai` dep + settings; prompt assembly, call, tagged parse | Output parsing robustness — mitigated by always-tagged + fallback |
| 2. View & JSON endpoint     | Generate page at `/` + validated JSON endpoint               | Ownership / one-per-group validation; ensuring zero persistence |
| 3. Frontend + JS            | Single-screen UI, toggle buttons, fetch, copy, errors        | Toggle-state correctness; clipboard fallback over plain HTTP    |
| 4. Docs & deploy config     | OpenRouter env vars/secrets in `.env.example`, `CLAUDE.md`, `deployment-steps.md`; `infrastructure.md` consistency check | Env-var name drift across docs — caught by a grep check        |

**Prerequisites:** F-01, F-02, S-01, S-02 (all done); an OpenRouter API key for manual verification.
**Estimated effort:** ~2–3 focused sessions; Phase 4 folds into the Phase 3 review.

## Open Risks & Assumptions

- LLM integration is the riskiest element (external API, key mgmt, latency) — isolated in the service layer and fully mockable.
- The always-tagged output contract relies on the model honoring tags; the no-`<body>` fallback prevents hard failures.
- Non-retention must be actively verified (test asserts zero DB rows; no input in logs/exceptions).
- Clipboard one-click may be unavailable over plain HTTP — select-all textarea fallback covers it (FR-012).

## Success Criteria (Summary)

- A logged-in user completes select → options → paste → generate → copy on `/` in under 60 seconds.
- Title appears (copyable) only for `generate_title` templates; body always appears, shown verbatim.
- API failure shows a friendly inline error with input preserved; no generation input/output is persisted or logged.
