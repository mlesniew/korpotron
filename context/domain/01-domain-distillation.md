---
title: "Korpotron — Domain Distillation"
created: 2026-06-25
type: domain-distillation
---

# Korpotron — Domain Distillation

> A MAP of the business domain distilled from the source documents and the code — not a code design. Every concept is
> traced to a source quote and to its location in the code (or marked **ABSENT from the code**). Citations are
> `path:line` ranges verified against the repository at the time of writing.

## Step 0 — Project context (discovery)

**Source documents found** (rich — this is _not_ a README-only project):

- `context/foundation/idea.md` — original problem/feature note (the seed vision).
- `context/foundation/prd.md` — the authoritative requirements doc (status: `implemented`, v1, greenfield web-app).
  Contains Vision, Success Criteria, User Stories, Functional Requirements (FR-001…FR-012), Business Logic, Non-Goals.
- `context/foundation/roadmap.md` — full delivery history (foundations F-01/F-02, slices S-01…S-11) with status and
  archive pointers.
- `context/foundation/adr/001-llm-provider-openrouter.md` — provider decision.
- `context/archive/**` — per-change `plan.md` / `plan-brief.md` / `reviews/` — an extended change history used here as
  primary source material (especially for the `is_response` deferral decision).
- `CLAUDE.md` — stack & conventions.

**Stack** (`CLAUDE.md`, `pyproject.toml`): Django 6.0.5 · Python 3.12 · uv · SQLite (dev) · Fly.io (prod) · OpenRouter
via the `openai` SDK · GitHub Actions CI.

**Where the business logic lives (layers):**

| Layer                      | Location                                 | Notes                                                                                             |
| -------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Domain model (persistence) | `core/models.py`                         | `Template`, `OptionGroup`, `Option`, `DailyGenerationCount`, `OnboardingState`                    |
| Domain service             | `core/llm.py`                            | prompt assembly (`build_messages`), OpenRouter call (`generate`), output parsing (`parse_result`) |
| API / application          | `core/views.py`                          | CRUD CBVs + `generate_api` function view (the orchestration of the core flow)                     |
| Forms / validation         | `core/forms.py`                          | `OptionFormSet`, option/registration validation                                                   |
| Onboarding (domain event)  | `core/apps.py`                           | `seed_onboarding_defaults` wired to `user_logged_in`                                              |
| Seed data                  | `core/fixtures/onboarding_defaults.json` | default templates + option groups                                                                 |
| Routing                    | `core/urls.py`                           | —                                                                                                 |
| Config                     | `korpotron/settings.py`                  | `OPENROUTER_*`, `DAILY_GENERATION_LIMIT`, `REGISTRATION_PASSPHRASE`                               |
| UI                         | `templates/`, `static/`                  | not central to the domain map                                                                     |

**Single bounded context.** The whole app is one small Django context; there are no service boundaries. The interesting
structure is _within_ the domain model and the generation flow, not across modules.

---

## Step 1 — Ubiquitous Language

Each row: **definition** · **source quote (doc)** · **code location** (or `ABSENT`).

### Template

A named, reusable transformation instruction — the saved "prompt" the user applies to text.

- Doc: _"User can create a template with a name, base prompt, generate-title flag, and is-response flag"_ —
  `context/foundation/prd.md:88` (FR-001).
- Code: `class Template` — `core/models.py:6-25`. Fields `name`, `base_prompt`, `generate_title` only.

### Base prompt

The core instruction text injected into the LLM request; the heart of a Template.

- Doc: _"**Base prompt** — the core instruction sent to the LLM"_ — `context/foundation/idea.md:24`.
- Code: `base_prompt = models.TextField()` — `core/models.py:13`; consumed at `core/llm.py:106`.

### Generate-title flag

Whether the transformation should also produce a short title/subject line.

- Doc: _"**Generate title** — whether a title or subject line should be produced"_ — `context/foundation/idea.md:25`.
- Code: `generate_title = models.BooleanField(default=False)` — `core/models.py:14`; drives the `TITLE_CONTRACT` branch
  at `core/llm.py:104`.

### Is-response flag (reply context)

Whether the text being transformed is a _reply_ to another message, unlocking an original-message input.

- Doc: _"User can enter the original message when the selected template has the is-response flag set"_ —
  `context/foundation/prd.md:120` (FR-010, nice-to-have).
- Code: **ABSENT from the code.** Deliberately deferred to v2 — _"`is_response` flag | Deferred to v2"_
  (`context/archive/2026-05-28-core-data-model/plan-brief.md:22`); _"`Template` has **no** `is_response` field"_
  (`context/archive/2026-06-01-text-generation-flow/plan.md:27`). See divergence D-1.

### Option group

A reusable, named set of mutually-exclusive option choices layered on top of a template (e.g. Tone, Language).

- Doc: _"User can create an option group with a name and a set of named options (each with instruction text)"_ —
  `context/foundation/prd.md:100` (FR-004).
- Code: `class OptionGroup` — `core/models.py:28-41`. Per-user; `unique_together = [("user", "name")]`.

### Option

A single selectable choice inside a group, carrying instruction text to inject into the prompt.

- Doc: _"**Options** — a set of selectable items, each with: A display name / The instruction text to inject into the
  prompt"_ — `context/foundation/idea.md:33-36`.
- Code: `class Option` — `core/models.py:44-68`. Fields `name`, `instruction`; FK `group`;
  `unique_together = [("group", "name")]`.

### Modifier instruction

The injected instruction text of an Option; constrained to a single non-blank line.

- Doc: _"The instruction text to inject into the prompt"_ — `context/foundation/idea.md:36`.
- Code: `instruction = models.TextField()` with `clean()` rejecting blank/multiline — `core/models.py:51,59-68` (error
  message names it _"Modifier instruction"_).

### One-option-per-group rule (mutual exclusivity)

At most one option per group may be active in a single transformation — the load-bearing composition guarantee.

- Doc: _"Option groups enforce mutual exclusivity within a group (e.g. Formal vs Casual under Tone). … Groups are a
  load-bearing design choice, not a nice-to-have."_ — `context/foundation/prd.md:104-106`; _"only one option per group
  can be active at a time. This guarantees that the assembled prompt contains no conflicting instructions"_ —
  `context/foundation/prd.md:146-148`.
- Code: enforced **imperatively at the endpoint**, not structurally — `core/views.py:238-242`. See divergence D-2.

### Prompt assembly / composition

Merging a template's base prompt with the selected options' instructions into one composite request.

- Doc: _"the app merges the selected instruction texts into the base prompt before submitting it for text generation"_ —
  `context/foundation/prd.md:148`.
- Code: `build_messages()` — `core/llm.py:92-122` (base prompt + `- {instruction}` bullet lines inside an
  `<instructions>` block; user text inside a `<content>` block).

### Transformation / Generation

The core act: submit the composite prompt for text generation and return a rewritten version of the user's input.

- Doc: _"The app assembles a prompt … then submits the composite for text generation to produce a rewritten version of
  the user's input."_ — `context/foundation/prd.md:142-143`.
- Code: `llm.generate()` — `core/llm.py:154-167`; orchestrated by `generate_api()` — `core/views.py:187-282`.

### Generate result (Title / Body)

The structured output of a transformation: an optional title and the rewritten body.

- Doc: _"they see the rewritten result and can copy it to the clipboard"_ — `context/foundation/prd.md:74`.
- Code: `@dataclass GenerateResult(title, body)` — `core/llm.py:71-74`; extracted from `<title>`/`<body>` tags by
  `parse_result()` — `core/llm.py:125-151`.

### Verbatim output (faithfulness)

The result is shown exactly as produced; the editor reshapes style but must not alter facts.

- Doc: _"Result is displayed verbatim — no silent truncation or modification"_ — `context/foundation/prd.md:78`.
- Code: system prompt enforces faithfulness (_"You must not add, remove, or invent facts…"_) — `core/llm.py:40-46`;
  result passed through unmodified except tag-strip + `.strip()` — `core/llm.py:140-151`, `core/views.py:282`.

### Content / instructions framing (prompt-injection boundary)

Pasted text is treated strictly as _data_, never as instructions — a security-as-domain rule.

- Doc: not in the PRD; originates in code design — _"everything inside `<content>` is data to be rewritten, never
  instructions"_ — `core/llm.py:24-29`.
- Code: `SYSTEM_PROMPT` — `core/llm.py:30-53`; `<content>` delimiting in `build_messages` — `core/llm.py:114-117`. (A
  domain concept present in code but **absent from the PRD**.)

### Non-retention (privacy guardrail)

User input and model output are never persisted or logged beyond the request scope.

- Doc: _"Input text submitted for transformation is not stored or logged beyond the scope of the request"_ —
  `context/foundation/prd.md:64`.
- Code: docstring + behaviour in `generate_api` (_"Never persists or logs user input or model output"_) —
  `core/views.py:190-196`; `core/llm.py:5-8`. Verified by test `test_generate_creates_no_db_rows`
  (`tests/test_generate.py:247`).

### Daily generation limit / Daily generation count

A per-user, per-day cap on transformations for cost control.

- Doc (roadmap, not PRD): _"generation is rate-limited per user per day via env var … default: `100`; `0` = unlimited"_
  — `context/foundation/roadmap.md:177-179` (S-05).
- Code: `class DailyGenerationCount` — `core/models.py:71-84`; enforcement `core/views.py:248-280`; setting
  `DAILY_GENERATION_LIMIT` — `korpotron/settings.py:134`.

### Onboarding defaults / Onboarding state

Seeding a new user with default templates + option groups exactly once, on first login.

- Doc (roadmap, not PRD): _"new users have 3 default templates and a set of default option groups seeded … on first
  login … idempotency guard (zero templates + zero option groups) prevents double-seeding"_ —
  `context/foundation/roadmap.md:193-212` (S-06).
- Code: `seed_onboarding_defaults` — `core/apps.py:16-53`; `class OnboardingState` — `core/models.py:87-96`; data in
  `core/fixtures/onboarding_defaults.json`.

### Registration passphrase

A shared invite code gating self-registration; valid code ⇒ immediately active account.

- Doc (roadmap, not PRD): _"users can register themselves … by providing a shared passphrase. Accounts are immediately
  active"_ — `context/foundation/roadmap.md:248-250` (S-11).
- Code: `UserRegistrationForm.clean_passphrase` (constant-time compare) — `core/forms.py:62-69`; gate in
  `RegisterView.dispatch` — `core/views.py:44-49`; setting — `korpotron/settings.py:136`.

### User ownership (tenancy)

Every Template and OptionGroup belongs to exactly one user; flat access, no sharing.

- Doc: _"Flat model — every logged-in user has full access … No role separation in the MVP."_ —
  `context/foundation/prd.md:155`; Non-Goal _"templates and option groups are per-user; no shared libraries"_ —
  `context/foundation/prd.md:164`.
- Code: `user = models.ForeignKey(...)` on `Template`/`OptionGroup` — `core/models.py:7-11,29-33`; per-user querysets
  everywhere (e.g. `core/views.py:60-61,79-80,99-104,216`).

---

## Step 2 — Subdomain classification (Core / Supporting / Generic)

Justified against the product goal: _"a purpose-built tool that is minimal, fast, and opinionated about the workflow —
not a general-purpose prompt library"_ (`context/foundation/prd.md:27-28`) and the primary success criterion (select →
options → text → generate → copy, under 60 s — `context/foundation/prd.md:53-60`).

| Area / concept                                                                                    | Category       | Justification (tied to product goals)                                                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Transformation flow** (prompt assembly + LLM call + verbatim result) — `llm.py`, `generate_api` | **Core**       | This _is_ the product. It's the North Star slice (S-03, `roadmap.md:26-29`) and the hypothesis under test: turning a multi-minute copy-paste chore into seconds.                                                            |
| **Template + Option-group composition model** with the **one-per-group invariant**                | **Core**       | The opinionated structure that differentiates this from a generic prompt library. The PRD explicitly calls groups _"a load-bearing design choice"_ whose exclusivity guarantees coherent output (`prd.md:104-106,146-148`). |
| **Faithfulness / verbatim guardrail + content/instructions injection boundary** (`SYSTEM_PROMPT`) | **Core**       | Output quality and "data not instructions" framing are what make the tool trustworthy for real emails; the differentiating editorial behaviour lives here (`llm.py:30-53`).                                                 |
| **Template management** (CRUD)                                                                    | **Supporting** | Necessary so users have prompts to apply, but it's conventional ownership-scoped CRUD; the value is in _using_ templates fast, not in managing them (`prd.md:88-96`, FR-001…003).                                           |
| **Option-group management** (CRUD + formset)                                                      | **Supporting** | Same: enables the core, not itself the advantage (`prd.md:100-110`, FR-004…006).                                                                                                                                            |
| **Onboarding defaults** (seed on first login)                                                     | **Supporting** | Reduces time-to-value but is product-specific glue, not the differentiator; post-MVP (S-06, `roadmap.md:191-213`).                                                                                                          |
| **Daily generation limit**                                                                        | **Generic**    | Generic cost-control/rate-limiting; not in the PRD, added for cost guardrails (S-05, `roadmap.md:176-189`).                                                                                                                 |
| **Authentication / registration / passphrase gate**                                               | **Generic**    | Standard Django auth + an invite code; PRD treats access control as a flat prerequisite (`prd.md:153-155`, S-11).                                                                                                           |
| **Landing page**                                                                                  | **Generic**    | Marketing entry point, no domain logic (S-04, `roadmap.md:162-173`).                                                                                                                                                        |

---

## Step 3 — Aggregate candidates and their invariants

For each: the business rule that must always hold, a source quote, and enforcement status — **enforced** (the
persistence layer guarantees it), **declared** (validation code exists but is bypassable), or **ignored**.

### A-1 — OptionGroup (root) aggregating Options

- **Inv-1: group name unique per user.** Doc: implied by per-user library + edit/rename. Code:
  `unique_together = [("user", "name")]` — `core/models.py:38`. **Enforced** (DB constraint, migration `0003`).
- **Inv-2: option name unique within the group.** Code: `unique_together = [("group", "name")]` — `core/models.py:54`
  - form check `core/forms.py:46-48`. **Enforced** (DB) and re-declared in the form.
- **Inv-3: a group has ≥ 1 option.** Doc: _"a set of named options"_ (`prd.md:100`). Code: `RequiredOptionInlineFormSet`
  _"At least one option is required."_ — `core/forms.py:42-43`. **Declared** at the form layer only — the model permits
  an empty group; `seed_onboarding_defaults` and any direct ORM write bypass it.
- **Inv-4: an option's instruction is a single non-blank line.** Doc: _"each with instruction text"_ (`prd.md:100`).
  Code: `Option.clean()` — `core/models.py:59-68` and `OptionForm.clean_instruction` — `core/forms.py:24-28`.
  **Declared** — Django does not call `full_clean()` on `save()`, so the CRUD form enforces it but
  `Option.objects.create(...)` in onboarding (`core/apps.py:49-52`) does not. See D-4.

### A-2 — Template

- **Inv-5: base prompt is non-blank.** Doc: _"a name, base prompt …"_ (`prd.md:88`). Code: `Template.clean()` strips and
  rejects blank — `core/models.py:22-25`. **Declared** — enforced via the CRUD ModelForm, bypassed by direct `.create()`
  (e.g. onboarding seeding).
- **Inv-6: every template is owned by one user.** Doc: _"per-user"_ (`prd.md:164`). Code: non-null FK —
  `core/models.py:7-11`; set in `form_valid` — `core/views.py:69-71`. **Enforced** (NOT NULL FK).

### A-3 — Transformation (a transient aggregate at generation time)

This aggregate has **no persistent identity** — it lives only for the duration of a request (consistent with the
non-retention NFR). Its invariants are runtime, in `generate_api`.

- **Inv-7 (the core invariant): at most one option per group in a single transformation.** Doc: _"only one option per
  group can be active at a time. This guarantees that the assembled prompt contains no conflicting instructions"_ —
  `prd.md:146-148`. Code: imperative check — `core/views.py:238-242`. **Declared** (endpoint-only; nothing structural
  stops a different caller). See D-2 — this is the #1 refactoring target.
- **Inv-8: all selected options/templates belong to the requesting user.** Doc: per-user ownership (`prd.md:164`). Code:
  ownership-scoped queries `core/views.py:216,228-236`. **Enforced** at the endpoint for this path.
- **Inv-9: user input/output is never persisted or logged.** Doc: `prd.md:64`. Code: `core/views.py:190-196`,
  `core/llm.py:5-8`. **Enforced by discipline** (and guarded by `test_generate_creates_no_db_rows`,
  `tests/test_generate.py:247`) — there is no structural mechanism, but no write path exists.

### A-4 — DailyGenerationCount

- **Inv-10: one counter row per (user, date).** Code: `unique_together = [("user", "date")]` — `core/models.py:81`.
  **Enforced** (DB).
- **Inv-11: count increments atomically and only on success.** Doc: rate-limit per day (`roadmap.md:177`). Code:
  `select_for_update` + `F("count") + 1` inside `transaction.atomic`, after a successful LLM call —
  `core/views.py:248-280`. **Enforced** (row-locked, transactional; increment skipped on LLM error — verified by
  `test_daily_limit_llm_error_does_not_increment`, `tests/test_generate.py:343`).

### A-5 — OnboardingState

- **Inv-12: a user is seeded at most once.** Doc: _"idempotency guard … prevents double-seeding"_ (`roadmap.md:211`).
  Code: `OneToOneField` + `select_for_update` guard + existence check — `core/models.py:88-92`, `core/apps.py:26-53`.
  **Enforced** (1:1 constraint + serialised guard).

---

## Step 4 — MODEL vs CODE divergences

The most valuable section: where the documents encode domain knowledge the code does not (yet) reflect.

| #       | The document says…                                                                                                                                                   | The code does…                                                                                                                                                                                                                                                        | Evidence                                                                                                                          | Severity                                                         |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **D-1** | Template has an **is-response flag** + original-message input (FR-001, FR-010).                                                                                      | No `is_response` field exists anywhere; the reply use-case is unimplemented. **Deliberate** v2 deferral, not an accident.                                                                                                                                             | Doc `prd.md:88,120`; absence confirmed `context/archive/2026-06-01-text-generation-flow/plan.md:27`; model `core/models.py:6-25`. | Low (intentional; PRD nice-to-have, parked `roadmap.md:336-338`) |
| **D-2** | Mutual exclusivity is **structural**: _"enforced by the option group structure, not by the user at generation time"_; groups make conflicting selections impossible. | Exclusivity is an **imperative endpoint check**. The data model places no constraint linking a transformation to one-option-per-group; any code path other than `generate_api` (a future API, a bulk action, a management command) can assemble a conflicting prompt. | Doc `prd.md:146-148,104-106`; code `core/views.py:238-242`; no model/DB constraint in `core/models.py`.                           | **High** (core invariant, weakly located)                        |
| **D-3** | _"the **composition rule is enforced by the option group structure**, not by the user"_ — implies the model carries the rule.                                        | The composition rule (which options merge, in what shape) lives entirely in the **service layer** (`build_messages`), decoupled from the model. Reasonable, but it means the "structure enforces it" claim is aspirational.                                           | Doc `prd.md:147`; code `core/llm.py:92-122`.                                                                                      | Medium                                                           |
| **D-4** | Model invariants read as guarantees: base prompt non-blank (FR-001), instruction a single non-blank line.                                                            | `clean()`/`Option.clean()` are **only** invoked by ModelForms. Onboarding seeding writes via `.objects.create(...)` with no `full_clean()`, so a malformed fixture would persist unvalidated.                                                                         | Doc `prd.md:88,100`; `clean()` at `core/models.py:22-25,59-68`; bypassing writes at `core/apps.py:41-52`.                         | Medium                                                           |
| **D-5** | Output is shown _"verbatim — no silent truncation or modification"_ (`prd.md:78`).                                                                                   | Output is faithful but **not byte-verbatim**: tags are stripped and `.strip()` is applied; on malformed output a 3-tier fallback reshapes what counts as title/body.                                                                                                  | Doc `prd.md:78`; code `core/llm.py:125-151`.                                                                                      | Low (acceptable; worth naming)                                   |
| **D-6** | PRD is silent on prompt-injection / "content is data, not instructions."                                                                                             | The code introduces a **first-class domain rule** (content/instructions framing, faithfulness contract) that the domain docs never capture — domain knowledge living _only_ in code.                                                                                  | Code `core/llm.py:24-53`; no PRD counterpart.                                                                                     | Medium (reverse divergence — undocumented)                       |
| **D-7** | PRD names **OAuth** as an auth option (_"email + password or OAuth"_, `prd.md:154`).                                                                                 | Only email/username + password and a passphrase-gated registration exist; no OAuth.                                                                                                                                                                                   | Doc `prd.md:154`; code `core/forms.py:62-69`, `core/views.py:39-54`. Parked in `roadmap.md:339-340`.                              | Low (intentional, parked)                                        |

---

## Step 5 — Refactoring ranking (value × risk)

Ranked by **value** (how core the invariant is to the product's advantage) and **risk** (how weakly it is enforced
today). High value + high risk = top priority.

| Rank   | Candidate / invariant                                                          | Value                                                                   | Enforcement risk                                                                      | Score   |
| ------ | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------- |
| **#1** | **Inv-7 / D-2 — one-option-per-group exclusivity**                             | **Core** — PRD calls it _"load-bearing"_; coherent output depends on it | **High** — lives in one imperative `if` at the endpoint, no structural backstop       | **Top** |
| #2     | D-4 — model `clean()` invariants bypassed on direct `.create()` (Inv-4, Inv-5) | Supporting (data integrity)                                             | High — silently bypassed by onboarding seeding & any ORM write                        | High    |
| #3     | D-6 — injection/faithfulness rule undocumented (Inv-9-adjacent)                | Core (trust/quality)                                                    | Medium — implemented well, but knowledge exists only in code; fragile to future edits | Medium  |
| #4     | Inv-3 — "group has ≥ 1 option" enforced only in the form                       | Supporting                                                              | Medium — empty groups can be created via non-form paths                               | Medium  |
| #5     | D-1 — is-response feature gap                                                  | Nice-to-have (v2)                                                       | Low — intentional, tracked                                                            | Low     |

### #1 recommendation — make the one-per-group invariant structural

**Why it's #1.** It is simultaneously the _most core_ rule (the PRD elevates option groups to _"a load-bearing design
choice"_ precisely because exclusivity is what prevents conflicting, incoherent prompts — `prd.md:104-106`) and the
_most weakly enforced_ (a single imperative comparison at `core/views.py:238-242`, with the data model permitting
exactly the state the rule forbids — D-2). The PRD's own words — _"enforced by the option group structure, not by the
user at generation time"_ — describe a guarantee the code does not actually provide. Today the guarantee holds only
because exactly one caller (`generate_api`) remembers to check; a second entry point silently reintroduces the
incoherent-output failure mode the design exists to prevent.

**Direction (not code):** model the _selection_ as a first-class value object — a `dict[group_id, option]` (or a
`Selection` type) built once, where adding a second option for a group is structurally impossible — and have both the
endpoint and `build_messages` consume that type. The invariant then lives with the data, so every future caller inherits
it. Pair it with calling `full_clean()` on the seeding path (#2) so the model's declared invariants become real
guarantees rather than form-only conventions.

---

## Limitations & method notes

- This map is distilled from rich source documents (PRD + roadmap + archived change history) **and** code — not a
  README-only project, so the Ubiquitous Language is well-grounded on both sides.
- Several genuinely load-bearing concepts (daily limit, onboarding, registration, injection boundary) live in the
  **roadmap/code but not the PRD** — the PRD froze at v1/MVP and post-MVP slices were tracked in the roadmap. Where a
  concept has no PRD home, the roadmap/code citation is given and the gap is noted (D-6).
- "Aggregate" is used in the DDD sense (a consistency boundary), not as an existing code abstraction — the codebase has
  plain Django models; the aggregate framing is the analytical contribution of this document.
- All `path:line` citations were verified against the working tree; no line numbers were assumed.
