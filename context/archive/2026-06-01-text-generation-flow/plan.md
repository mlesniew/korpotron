# Text Generation Flow Implementation Plan

## Overview

S-03 is the north-star slice: the smallest end-to-end flow that proves Korpotron's hypothesis — that a purpose-built template + LLM flow eliminates the copy-paste chore. At `/`, a logged-in user selects one of their templates, optionally toggles one option per option group, pastes the text to transform, clicks Generate, and sees a copyable **title** (when the template requests one) and **body** — all without leaving the page. Generation calls OpenRouter via the `openai` SDK; the user's input is never persisted or logged.

## Current State Analysis

The prerequisites (F-01 auth, F-02 models, S-01 template management, S-02 option-group management) are all built and merged.

- **Models** (`core/models.py`): `Template` (`name`, `base_prompt`, `generate_title` — note `is_response` was deferred to v2 and does **not** exist), `OptionGroup` (`name`, per-user, `unique_together` on `(user, name)`), `Option` (`name`, `instruction`, FK to group). Mutual exclusivity (one option per group) is **not** a DB constraint — it is enforced at selection time in the UI/endpoint.
- **View conventions** (`core/views.py`): class-based views with `LoginRequiredMixin`; per-user isolation via `get_queryset` filtering on `self.request.user`; `reverse_lazy` success URLs. The existing flow is pure CRUD — this slice introduces the first bespoke, non-CRUD view.
- **URL wiring**: `korpotron/urls.py` mounts `core.urls` at root and `korpotron.views.home` at `/` (currently a `@login_required` placeholder rendering `templates/home.html`). `core/urls.py` holds the CRUD routes.
- **Templates**: `templates/base.html` (Bootstrap 5.3 via CDN, navbar with auth-gated links), server-rendered, vanilla JS for dynamic bits (see the formset row-adding script in `templates/core/optiongroup_form.html`). No JS framework, no build step.
- **Tests** (`tests/`): pytest + pytest-django, Django `Client`, per-user isolation assertions, `user`/`other_user` fixtures in `conftest.py`. ADR 001 prescribes mocking `chat.completions.create` with `unittest.mock.patch`.
- **LLM provider** (ADR 001 + `tech-stack.md`): OpenRouter via `openai` SDK with `base_url="https://openrouter.ai/api/v1"`, model from `OPENROUTER_MODEL`, key from `OPENROUTER_API_KEY`. **`openai` is not yet a dependency** (`pyproject.toml`).
- **Settings** (`korpotron/settings.py`): env-driven via `os.environ` + `python-dotenv`. `.env.example` documents local vars. No LLM config present yet.

## Desired End State

A logged-in user visiting `/` sees a single screen: a template picker, a text box for the input, button groups (one per option group) beneath it, and a Generate button. On Generate, a spinner shows while the request is in flight; the result then appears as a body field (and a title field when the template's `generate_title` is on), each independently copyable. Errors surface as a dismissible inline alert without losing the user's input. No generation input or output is written to the database or logs.

Verify by: logging in, configuring a template + an option group, performing the full flow under 60 seconds, and confirming (a) the result is shown verbatim, (b) copy works, (c) a forced API error shows a friendly alert with input preserved, and (d) no DB rows or log lines contain the input text.

### Key Discoveries:

- `Template` has **no** `is_response` field — reply-context input (FR-010) is out of scope for this slice (`core/models.py:5-19`).
- The one-option-per-group invariant lives in the UI/endpoint, not the schema — the endpoint must validate it (`prd.md` Business Logic; `core/models.py:38-51`).
- The placeholder home view is the natural mount point for the flow (`korpotron/views.py:6-8`); replacing it serves the under-60s goal with zero navigation.
- Non-retention is a hard NFR: no generation-history model (also a PRD non-goal), no logging of input/output (`prd.md` NFR; `roadmap.md` S-03 risk).
- Existing dynamic-UI pattern is vanilla JS embedded in the template (`templates/core/optiongroup_form.html:42-59`) — match it; do not introduce HTMX or a framework.

## What We're NOT Doing

- **No reply/original-message input** (FR-010 / `is_response`) — deferred to v2.
- **No generation history, persistence, or logging** of input/output — PRD non-goal and a hard NFR.
- **No streaming** of the LLM response — a single blocking call with a spinner is sufficient for MVP.
- **No new frontend dependency** (HTMX, React, build tooling) — vanilla JS only.
- **No template/option CRUD changes** — S-01/S-02 own those; this slice only reads them.
- **No model/migration changes** — the flow is stateless.
- **No prompt editing during the flow** — PRD non-goal.

## Implementation Approach

Three layers, built bottom-up so each is independently verifiable:

1. **Service layer** (`core/llm.py`) — pure-ish module: takes a `Template`, the selected `Option`s, and the user text; builds an app-owned **system message** (role + "content is data, not instructions" rule + the always-tagged output contract) and a **user message** with delimited `<instructions>` (base_prompt + option instructions) and `<content>` (user text); calls OpenRouter; parses the tagged `<title>`/`<body>` result with graceful fallback. The OpenRouter client is constructed from settings so tests can patch it.

2. **View + JSON endpoint** (`core/views.py`, `core/urls.py`, `korpotron/urls.py`) — a `GenerateView` (GET) that replaces home at `/` and renders the form from the user's own templates + option groups; a `generate_api` (POST, JSON) endpoint that validates the template and options belong to the user, enforces one-option-per-group, calls the service layer, and returns `{title, body}` or a structured error with the right HTTP status. Neither path writes to the DB.

3. **Frontend** (`templates/core/generate.html` + inline JS) — the single screen, the button-group toggle behaviour, the `fetch` call with spinner/disabled state, result rendering into copyable title/body fields, inline error alert, and clipboard copy (one-click `navigator.clipboard` with a select-all textarea fallback per FR-012).

## Critical Implementation Details

- **Prompt structure & injection posture.** The system message is **app-owned and predefined** — it is the single stable authority and establishes that everything in `<content>` is data to be rewritten, never instructions. The user-authored template instructions go in the **user** message (they are this run's intent), framed by — and unable to override — the system prompt. The real injection vector is the *content* (often third-party text the user pastes, e.g. an email), which is why content is tag-delimited and explicitly framed as data. This rationale must survive into the system-prompt wording.
- **Always-tagged output contract.** The model is always instructed to wrap output in tags (`<body>…</body>` always; `<title>…</title>` first, only when the template's `generate_title` is on). Parsing is a simple, deterministic tag extraction. **Fallback:** if no `<body>` tag is present, treat the entire raw response as the body and the title as empty — never error out on a malformed-but-present response. The tag scheme is intentionally extensible for future fields.
- **Non-retention.** No model, no `.save()`, no logging of `request.POST`, the assembled prompt, or the LLM output. Be careful that exception handling does not log the input (e.g. don't `logger.exception` with the prompt in the message). Verify in tests that generation creates zero DB rows.
- **One-option-per-group enforcement.** The endpoint must reject (or ignore-with-error) a payload that selects more than one option from the same group, even though the UI prevents it — the JSON endpoint is directly POST-able.

## Phase 1: LLM Service Layer

### Overview

Add the `openai` dependency and OpenRouter settings, then build `core/llm.py`: prompt assembly, the OpenRouter call, and tagged-result parsing. Fully unit-tested with the client mocked — no network.

### Changes Required:

#### 1. Dependency

**File**: `pyproject.toml` (via `uv add openai`)

**Intent**: Add the `openai` SDK as a runtime dependency so the service layer can talk to OpenRouter. Run `uv add openai` (do not hand-edit) so `uv.lock` updates.

**Contract**: `openai` appears under `[project].dependencies`; `uv.lock` regenerated.

#### 2. Settings & env config

**File**: `korpotron/settings.py`, `.env.example`

**Intent**: Expose `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` (with a sensible default), and the fixed `OPENROUTER_BASE_URL` to the app, read from the environment per the existing `os.environ` pattern. Document them in `.env.example`.

**Contract**: Settings module exposes `OPENROUTER_API_KEY: str`, `OPENROUTER_MODEL: str` (default e.g. `openai/gpt-4o-mini`), `OPENROUTER_BASE_URL: str` (default `https://openrouter.ai/api/v1`). The API key is read but **not** required at import time in a way that breaks tests (tests patch the client) — default to empty string and let the call fail loudly only when actually invoked. `.env.example` gains commented entries for all three.

#### 3. Service module

**File**: `core/llm.py` (new)

**Intent**: Provide the prompt-assembly, OpenRouter-call, and result-parsing logic as small typed functions. Keep the OpenRouter client construction in a thin factory so tests can patch it. The system prompt (app-owned) and tag scheme live here as module constants.

**Contract**:
- A function that builds the messages list from `(template, selected_options, text)` → `list[dict]` with a system message (constant app prompt incl. the always-tagged output contract; title requested iff `template.generate_title`) and a user message containing `<instructions>…</instructions>` (base_prompt + each option's instruction) and `<content>…</content>` (user text).
- A function that takes the raw model string and returns a typed result `(title: str, body: str)` — extract `<title>`/`<body>` by tag; if `<body>` absent, `body = raw.strip()`, `title = ""`.
- A top-level `generate(template, selected_options, text) -> GenerateResult` that builds messages, calls `client.chat.completions.create(model=..., messages=...)`, and parses the response. The OpenRouter client is obtained from a module-level factory (e.g. `_get_client()`) reading settings — patch target for tests. The client is constructed with an **explicit request timeout of 60s** (the rewrite task is short and should complete well within this) so a stalled upstream surfaces as `openai.APITimeoutError` rather than hanging the worker indefinitely (the SDK default is 600s).
- Type hints throughout (project convention; mypy in CI).

### Success Criteria:

#### Automated Verification:

- Dependency resolves: `uv sync` succeeds and `openai` is importable.
- Unit tests pass: `uv run pytest tests/test_llm.py`
- Type checking passes: `uv run mypy core/llm.py` (or project-wide mypy)
- Linting passes: `uv run ruff check .` and `uv run ruff format --check .`

#### Manual Verification:

- With real `OPENROUTER_API_KEY` set in `.env`, a quick `uv run manage.py shell` call to `core.llm.generate(...)` returns a sensible rewrite.
- Output parsing handles a real title-on response (title + body separated correctly).

**Implementation Note**: After completing this phase and all automated verification passes, pause for manual confirmation before proceeding.

---

## Phase 2: Generate View & JSON Endpoint

### Overview

Replace the placeholder home view with the generate page (GET), and add the JSON POST endpoint that validates ownership + the one-per-group invariant, calls the service layer, and returns the result or a structured error. View tests use a mocked client and assert per-user isolation and non-retention.

### Changes Required:

#### 1. Generate page view (replaces home)

**File**: `core/views.py`, `korpotron/urls.py`, `korpotron/views.py`

**Intent**: Add a `LoginRequiredMixin` `GenerateView` (TemplateView-style, GET only) that renders `core/generate.html` with the current user's templates and option groups (each group prefetching its options). Mount it at `/` in place of `korpotron.views.home`; remove the now-dead placeholder home view and `templates/home.html`. Keep the navbar links working.

**Contract**: `GET /` returns 200 for an authenticated user, 302 to login otherwise. Context provides `templates` (user's, ordered) and `option_groups` (user's, with `.options`). Route `name="home"` is preserved (base template and `LOGIN_REDIRECT_URL=/` depend on it) or all references updated consistently.

#### 2. Generation JSON endpoint

**File**: `core/views.py`, `core/urls.py`

**Intent**: Add a login-required POST endpoint that accepts the template id, selected option ids, and text; validates the template and every option belong to the requesting user; enforces at most one option per group; calls `core.llm.generate`; and returns JSON. On LLM/transport failure, return a structured error with a non-500 status so the frontend can show a friendly alert. Never persist or log the input/output.

**Contract**:
- Route e.g. `POST /generate/` (`name="generate-api"`), `login_required`, JSON request body (`{template_id, option_ids: [...], text}`).
- Validation: `template_id` resolved via a user-scoped queryset (404/400 if not owned); each `option_id` resolved via options whose `group.user == request.user`; reject if two selected options share a `group_id` (400 with message). Empty `text` → 400.
- Success: `200 {"title": str, "body": str}` (title `""` when not requested).
- LLM failure: caught, mapped to `502 {"error": "<friendly message>"}` (or similar non-500) — no stack trace or input echoed in the body or logs. This includes `openai.APITimeoutError` (the 60s client timeout) so a stalled upstream resolves to the same friendly alert rather than hanging.
- No DB writes on any path.

### Success Criteria:

#### Automated Verification:

- Endpoint + view tests pass: `uv run pytest tests/test_generate.py`
- Tests assert: login required; GET `/` lists only the user's templates/groups; successful POST returns parsed title/body (client mocked); cross-user template/option ids are rejected; two-options-same-group rejected; LLM exception → error status, not 500; **no DB rows created** during generation.
- Type checking passes: `uv run mypy core`
- Linting passes: `uv run ruff check .`

#### Manual Verification:

- Hitting `/` shows the user's own templates and option groups only.
- A malformed/cross-user POST (via curl) is rejected as specified.

**Implementation Note**: After completing this phase and all automated verification passes, pause for manual confirmation before proceeding.

---

## Phase 3: Frontend (Generate Page + JS)

### Overview

Build the single-screen UI and its vanilla JS: template picker, text box, option button groups with toggle/deselect behaviour, Generate with spinner, copyable title/body result, and inline error alert.

### Changes Required:

#### 1. Generate page template

**File**: `templates/core/generate.html` (new), `templates/base.html` (nav link if desired)

**Intent**: Render the flow on one screen, extending `base.html`. Order top-to-bottom: template `<select>`, the input `<textarea>`, then one button group per option group (group name as heading above each), then the Generate button, then a result region (hidden until populated) and an error alert region (hidden until needed). Each option group is a Bootstrap button group of toggle `<button>`s; the selected option id per group is tracked in a hidden input (or JS state) so the fetch payload can be assembled.

**Contract**: Markup exposes stable hooks for the JS (template select, textarea, per-group containers carrying their `group_id`, each option button carrying its `option_id`, generate button, result title/body fields, copy buttons, error region). Result title field is shown only when present. **Empty state**: when the user has no templates, render a short prompt with a link to `{% url 'template-create' %}` instead of the form (the north-star landing screen must not present an empty picker + a Generate button that 400s). Uses existing Bootstrap classes; no new CSS framework.

#### 2. Flow JavaScript

**File**: inline `<script>` in `templates/core/generate.html` (matching the existing inline-JS pattern)

**Intent**: Implement (a) button-group toggle: clicking an option selects it and deselects siblings in the same group; clicking the selected one again clears the group; (b) Generate: gather `template_id`, selected `option_ids`, and `text`, POST JSON to the endpoint with the CSRF token, disable the button and show a spinner while in flight (use an `AbortController` with a client-side timeout slightly above the 60s server timeout so the spinner always resolves to either a result or the inline error); (c) on success, render body (and title when returned) into copyable fields and reveal the result region; (d) on error, show the inline alert with the endpoint's message and re-enable the button, preserving all input; (e) clipboard copy: `navigator.clipboard.writeText` with a select-all-on-a-textarea fallback per FR-012.

**Contract**: CSRF handled via the Django cookie/token (the page is same-origin) — read the `csrftoken` value from `document.cookie` and send it as the `X-CSRFToken` header on the fetch (the JSON POST is not a Django form submit, and the cookie is already set because `base.html` renders `{% csrf_token %}` in the logout form). The result title/body are written into the copyable fields via `element.value` (textarea/input) or `textContent` — **never `innerHTML`** — so output is shown verbatim and HTML in the result/pasted content cannot execute. Loading state visibly distinct; only one in-flight request at a time. Toggle state is the single source of truth for the payload. No external JS libraries.

### Success Criteria:

#### Automated Verification:

- Page renders: `uv run pytest tests/test_generate.py` (template-rendering assertions — e.g. group names and option buttons present in the GET response).
- Linting passes: `uv run ruff check .`
- Docker build succeeds: `docker build .` (per lessons.md — verify before committing).

#### Manual Verification:

- Full flow under 60 s: select template → toggle options → paste text → Generate → copy result.
- Button-group toggle behaves: select, switch, click-to-deselect all work; never more than one selected per group.
- Title shows only for `generate_title` templates; body always shows; both copy correctly (and the fallback works if `navigator.clipboard` is unavailable, e.g. over plain HTTP).
- Spinner shows during the call; a forced API failure shows the inline alert with input preserved and the button re-enabled.
- Result is shown verbatim (no truncation/modification).

**Implementation Note**: After completing this phase and all automated verification passes, pause for final manual confirmation.

---

## Phase 4: Documentation & Deployment Config

### Overview

Update the onboarding and deployment docs so the new OpenRouter dependency is reproducible by a fresh developer and a fresh deploy. The `.env.example` change ships in Phase 1 (the settings work needs it); this phase covers the human-facing docs that reference environment/secrets. No code changes.

### Changes Required:

#### 1. Deployment secrets

**File**: `context/deployment/deployment-steps.md`

**Intent**: Add `OPENROUTER_API_KEY` (and, if non-default, `OPENROUTER_MODEL`) to the Fly secrets step so a fresh deploy can generate text. Note that setting a secret on an already-running app does not take effect until a redeploy or machine restart (consistent with `infrastructure.md`'s risk register).

**Contract**: Section 2 ("Set Fly secrets") gains a `fly secrets set OPENROUTER_API_KEY="..."` line; a one-line caveat about secrets not being picked up by the running machine until `fly deploy` / `fly machine restart`. Wording stays consistent with `infrastructure.md` (which already lists this secret in its Getting Started step).

#### 2. Project onboarding doc

**File**: `CLAUDE.md`

**Intent**: Surface the LLM provider in the stack line and clarify the env-var story — the app runs locally without `OPENROUTER_API_KEY`, but the generation feature fails until it is set; `OPENROUTER_MODEL` is optional with a default.

**Contract**: Stack line mentions OpenRouter (LLM). The "Environment variables" section notes `OPENROUTER_API_KEY` is required for the generation flow to function locally (distinct from `SECRET_KEY`, which is required to boot), and that `OPENROUTER_MODEL` / `OPENROUTER_BASE_URL` have sensible defaults.

#### 3. Infrastructure doc (verify, edit only if stale)

**File**: `context/foundation/infrastructure.md`

**Intent**: Confirm the infrastructure doc already documents the OpenRouter secret (it does — Getting Started step 4 and the risk register both reference `OPENROUTER_API_KEY`). Edit only if the `.env.example` / `deployment-steps.md` additions introduce an inconsistency (e.g. a differing model-default or var name).

**Contract**: No edit expected. If touched, the `tech_stack.llm_provider` frontmatter, Getting Started, and risk register stay internally consistent with the var names settled in Phase 1.

### Success Criteria:

#### Automated Verification:

- Env var names in `.env.example`, `CLAUDE.md`, `deployment-steps.md`, and `infrastructure.md` match those read in `korpotron/settings.py`: `grep -r OPENROUTER context/ CLAUDE.md .env.example korpotron/settings.py` shows consistent names.

#### Manual Verification:

- A fresh developer following `CLAUDE.md` + `.env.example` can run the generation flow locally.
- A fresh deploy following `deployment-steps.md` sets all required secrets, including `OPENROUTER_API_KEY`.
- No env-var name or model-default contradictions across the four docs.

**Implementation Note**: Documentation-only phase; no pause required — fold into the same review as Phase 3.

---

## Testing Strategy

### Unit Tests (`tests/test_llm.py`):

- Message assembly: system message contains the app prompt + tagged-output contract; title requested iff `generate_title`; user message contains `<instructions>` (base_prompt + each selected option's instruction, in deterministic order) and `<content>` (the text), correctly delimited.
- Result parsing: title-on tagged response → `(title, body)`; body-only response → `("", body)`; **no `<body>` tag → whole raw string becomes body, title empty** (graceful fallback).
- `generate()` calls `chat.completions.create` with the configured model and the assembled messages (client mocked).

### Integration Tests (`tests/test_generate.py`):

- `GET /` requires login; lists only the user's own templates and option groups (cross-user isolation).
- `POST /generate/` happy path (client mocked) returns parsed `{title, body}`.
- Validation: cross-user `template_id` rejected; cross-user `option_id` rejected; two options from the same group rejected; empty text rejected.
- LLM exception → mapped error status (not 500), no input echoed; a timeout (`openai.APITimeoutError`) maps to the same friendly error.
- **Non-retention**: assert generation creates zero DB rows (e.g. compare model counts before/after).

### Manual Testing Steps:

1. Configure a template (one with `generate_title` on, one off) and an option group with 2+ options.
2. Run the full flow for the title-off template; confirm body-only result and copy.
3. Run it for the title-on template; confirm separate title + body, both copyable.
4. Exercise toggle: select, switch, deselect-to-none across a group.
5. Force a failure (bad API key) and confirm the inline alert + preserved input.
6. Time the full flow — confirm under 60 s.

## Performance Considerations

The single blocking LLM call dominates latency (seconds); the spinner covers it. The ~50–150 ms OpenRouter proxy hop (ADR 001) is negligible against the 60-second success criterion. `conn_max_age=600` already pools DB connections; the flow does no heavy queries (prefetch options on the GET).

## Migration Notes

None — no schema or data changes. The only data-shape change is removing the placeholder `templates/home.html` and repointing `/`.

## References

- Roadmap slice: `context/foundation/roadmap.md` (S-03, north star)
- PRD: `context/foundation/prd.md` (FR-007–FR-012, US-01, Business Logic, NFR non-retention)
- LLM provider decision: `context/foundation/adr/001-llm-provider-openrouter.md`
- Existing view/test patterns: `core/views.py`, `tests/test_template_views.py`
- Inline-JS dynamic-form pattern to match: `templates/core/optiongroup_form.html:42-59`
- Lessons: `context/foundation/lessons.md` (verify Docker build before committing)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: LLM Service Layer

#### Automated

- [x] 1.1 Dependency resolves: `uv sync` succeeds and `openai` is importable — d4d754e
- [x] 1.2 Unit tests pass: `uv run pytest tests/test_llm.py` — d4d754e
- [x] 1.3 Type checking passes: `uv run mypy core/llm.py` — d4d754e
- [x] 1.4 Linting passes: `uv run ruff check .` and `uv run ruff format --check .` — d4d754e

#### Manual

- [x] 1.5 Real `generate(...)` call via shell returns a sensible rewrite — d4d754e
- [x] 1.6 Title-on response parses into separated title + body — d4d754e

### Phase 2: Generate View & JSON Endpoint

#### Automated

- [x] 2.1 Endpoint + view tests pass: `uv run pytest tests/test_generate.py` — 88ce506
- [x] 2.2 Tests assert login-required, per-user listing, parsed result, cross-user rejection, same-group rejection, LLM-failure mapping, and zero DB writes — 88ce506
- [x] 2.3 Type checking passes: `uv run mypy core` — 88ce506
- [x] 2.4 Linting passes: `uv run ruff check .` — 88ce506

#### Manual

- [x] 2.5 `/` shows only the user's own templates and option groups — 88ce506
- [x] 2.6 Malformed/cross-user POST rejected as specified (curl) — 88ce506

### Phase 3: Frontend (Generate Page + JS)

#### Automated

- [x] 3.1 Page-rendering assertions pass: `uv run pytest tests/test_generate.py` — 7b75825
- [x] 3.2 Linting passes: `uv run ruff check .` — 7b75825
- [x] 3.3 Docker build succeeds: `docker build .` — 0017433

#### Manual

- [x] 3.4 Full flow completes under 60 s (select → toggle → paste → generate → copy) — 7b75825
- [x] 3.5 Button-group toggle: select, switch, click-to-deselect; never >1 per group — 7b75825
- [x] 3.6 Title shows only for `generate_title` templates; body always; both copy (incl. fallback) — 7b75825
- [x] 3.7 Spinner during call; forced failure shows inline alert with input preserved — 7b75825
- [x] 3.8 Result shown verbatim (no truncation/modification) — 7b75825

### Phase 4: Documentation & Deployment Config

#### Automated

- [x] 4.1 `OPENROUTER` var names consistent across `.env.example`, `CLAUDE.md`, `deployment-steps.md`, `infrastructure.md`, and `korpotron/settings.py` — 067d533

#### Manual

- [x] 4.2 Fresh developer can run the generation flow locally following `CLAUDE.md` + `.env.example` — 067d533
- [x] 4.3 Fresh deploy following `deployment-steps.md` sets `OPENROUTER_API_KEY` — 067d533
- [x] 4.4 No env-var name or model-default contradictions across the four docs — 067d533
