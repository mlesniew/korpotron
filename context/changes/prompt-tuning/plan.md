# Prompt Tuning for Better Output Quality — Implementation Plan

## Overview

The text this app produces is low quality: on lightweight OpenRouter models the rewriter behaves like a generative
assistant — it invents facts, embellishes, and occasionally drops the structured output tags. This plan tunes the prompt
layer to fix that without any structural change:

1. Rewrite `SYSTEM_PROMPT` to add a **facts-protecting (but style-permitting) faithfulness constraint**, a tighter
   **"style-transfer editor"** role, a **silent chain-of-thought anchor**, and an **explicit output-format example**.
2. Harden `parse_result()` so partial tag compliance no longer silently drops the title.
3. De-personalize the three built-in fixture templates (remove the conflicting "You are an experienced…" persona
   sub-frames) and double-anchor faithfulness at the task level.
4. Add a standalone `tools/eval_prompts.py` to compare prompt variants over a curated synthetic corpus, so quality
   changes can be verified before/after instead of by spot-checking the UI.

Locking the production `OPENROUTER_MODEL` to a specific free model is **out of scope** and recorded as a follow-up risk.

## Current State Analysis

- **`SYSTEM_PROMPT`** (`core/llm.py:30-41`) has injection protection (content-as-data), an "always wrap in `<body>`"
  contract, and a markdown directive — but **no faithfulness constraint** and a generic "writing assistant" role that
  frames the model as an _improver_, not an _editor_. This is the highest-leverage gap (research P0).
- **`TITLE_CONTRACT`** (`core/llm.py:44-47`) is prose-only ("put it inside `<title>...</title>`") with no concrete
  format example. Lightweight models comply with XML more reliably when shown the literal expected structure.
- **`parse_result()`** (`core/llm.py:112-126`) is all-or-nothing: if there is no `<body>` tag it returns the entire raw
  response as the body and drops the title — even when a `<title>` tag is present.
- **Fixture templates** (`core/fixtures/onboarding_defaults.json`): "Professional Email", "Jira Ticket", and "Meeting
  notes" each open with a persona sub-frame ("You are an experienced corporate communication specialist…", "You are a
  senior software engineer…"). These **contradict the system role** and, on cheap models, cause role confusion — the
  model "acts" as the persona and invents appropriate business context rather than transforming the source.
- **Fixture option/modifier instructions are already good** — contrary to research Section 4 (which described an older
  fixture), the current options are mostly imperative and specific ("Use natural and conversational language. Sound like
  a competent colleague."). **No modifier rewrite is needed.**
- **No eval tooling exists** — `tools/` holds only `review.py`. `build_messages()` (`core/llm.py:79-109`) is a pure
  function (Template + [Option] + str → messages), so it is trivially callable from a script without a network call.
- **Existing tests** (`tests/test_llm.py`) assert on prompt _structure_ (`"<body>" in system`, markdown directive,
  bullet ordering) rather than exact strings, so the wording rewrite mostly survives; only the parser needs new cases.
- **Non-retention NFR** (`core/llm.py:5`): no generation input/output is persisted — the eval corpus must be synthetic,
  and the eval log must be gitignored.

## Desired End State

- The default (uncustomized) output preserves the facts, names, numbers, dates, and claims of the source while still
  honoring deliberately creative modifiers (Shakespeare, Korpotron Ultra, Kawaii, Passive-Aggressive).
- The model reliably emits `<body>` (and `<title>` when requested); when it partially complies, the parser recovers the
  title instead of dropping it.
- The three built-in templates describe the _desired output_, not a persona, and each restates the faithfulness anchor.
- A developer can run `uv run python tools/eval_prompts.py` to see, per synthetic input, how a candidate prompt variant
  differs from the current one — with a gitignored JSONL log for later review.

Verify by: `uv run pytest` green, `uv run ruff check .` clean, fixture loads via `loaddata`, and a manual eval run shows
the new prompt suppressing invented content on the faithfulness-stress inputs.

### Key Discoveries:

- `SYSTEM_PROMPT` is the single highest-impact lever — `core/llm.py:30-41` (research P0).
- `build_messages()` is a pure function — `core/llm.py:79-109` — the correct seam for the eval harness (no network).
- Existing tests assert structure not exact wording — `tests/test_llm.py:33-42,117-122` — so the rewrite is low-risk.
- The fixture modifiers are already imperative/specific — `core/fixtures/onboarding_defaults.json:37-137` — only the
  three template `base_prompt`s carry the persona problem.
- Non-retention NFR forces synthetic eval inputs and a gitignored log — `core/llm.py:5`.

## What We're NOT Doing

- **Not** locking the production `OPENROUTER_MODEL` (stays `openrouter/auto:free`) — recorded as a follow-up.
- **Not** rewriting the option/modifier instructions — they are already imperative and specific.
- **Not** adopting JSON structured outputs / `response_format` — staying with the improved XML + parser-cascade approach
  (no per-model support detection needed).
- **Not** adding DeepEval / G-Eval scoring — the eval tool is diff + JSONL log only for this change.
- **Not** introducing a "Faithful/Strict" user-facing modifier — faithfulness is baked into the system prompt as the
  quality floor.
- **Not** persisting any real user data — eval corpus is synthetic, log is gitignored.

## Implementation Approach

Four independent, individually verifiable phases. Phases 1–2 are both in `core/llm.py` + `tests/test_llm.py` but kept
separate so the prompt-wording change and the parser-logic change can be reviewed and verified on their own. Phase 3 is
pure fixture content. Phase 4 is a standalone dev utility that never imports Django models directly beyond `build_*`
helpers and is not wired into CI.

The faithfulness constraint is framed as **protect facts, allow style**: it forbids adding/removing facts, names,
numbers, dates, and claims, while explicitly permitting tone, framing, vocabulary, flourish, and emojis — so the
creative modifiers that are the product's personality keep working.

## Critical Implementation Details

- **Faithfulness wording must scope to "substantive information", not "exactly the same content."** The research's
  literal "no more, no less" phrasing would fight the deliberately heavy-transform modifiers. The clause must permit
  stylistic additions (archaic phrasing, kamoji, buzzwords) while forbidding new _facts/claims_. Word the positive
  permission list ("you may change: word choice, structure, tone, formality, voice, and stylistic flourishes") and the
  negative list ("you must not change or invent: facts, names, numbers, dates, or the meaning of any claim") explicitly.
- **The silent-CoT anchor must say "silently."** "Before writing, silently note the key facts…" triggers the reasoning
  without leaking a scratchpad into the `<body>` output.
- **`TITLE_CONTRACT` is appended to the system message** (`core/llm.py:91`) only when `template.generate_title` is true.
  The format example in the base `SYSTEM_PROMPT` must show the body-only shape; `TITLE_CONTRACT` extends it to show the
  title+body shape. Existing test `test_build_messages_system_has_app_prompt_and_tag_contract` asserts `<title>` is
  **absent** when no title is requested — keep the title example out of the base prompt.

## Phase 1: System Prompt & Output Contract

### Overview

Rewrite `SYSTEM_PROMPT` and `TITLE_CONTRACT` to add the faithfulness constraint, the editor role, the silent-CoT anchor,
and an explicit output-format example. Update the structural unit tests to assert the new clauses are present.

### Changes Required:

#### 1. SYSTEM_PROMPT rewrite

**File**: `core/llm.py:30-41`

**Intent**: Replace the generic "writing assistant" role with a "style-transfer editor" role; add a facts-protecting
faithfulness block (negative prohibition + positive permission list + scope-bounding), a silent chain-of-thought anchor,
and an explicit `<body>` output-format example. Preserve the existing injection-protection clause verbatim and keep the
markdown directive.

**Contract**: `SYSTEM_PROMPT` remains a module-level `str`. It must still contain the substring `<body>`, the markdown
directive, and the content-as-data injection clause (existing tests depend on these). It must NOT contain `<title>` (the
title example belongs to `TITLE_CONTRACT`). New required substrings the tests will assert on: a faithfulness marker
(e.g. the words "facts" and "not add"/"invent") and the role phrase ("style-transfer editor"). The faithfulness block
must permit stylistic change and forbid only substantive/factual change — see Critical Implementation Details.

#### 2. TITLE_CONTRACT format example

**File**: `core/llm.py:44-47`

**Intent**: Extend the title contract from prose to a concrete two-tag example so lightweight models reliably emit both
tags in the right order.

**Contract**: `TITLE_CONTRACT` stays a module-level `str` appended to the system message when `generate_title` is true.
It must contain both `<title>` and `<body>` and show `<title>` before `<body>`. Appending it must keep
`SYSTEM_PROMPT + TITLE_CONTRACT` valid (no duplicated/conflicting body example).

#### 3. Update structural unit tests

**File**: `tests/test_llm.py:33-51,117-122`

**Intent**: Update/extend the prompt-structure assertions to lock in the new clauses without asserting brittle exact
strings.

**Contract**: Keep existing assertions that still hold (`<body>` present, `<title>` absent without title, markdown
directive, user text absent from system). Add assertions for: faithfulness clause present (assert on stable keywords,
e.g. `"facts"` and a not-add/invent marker), role phrase present, and — for the title path — `<title>` appears before
`<body>` in the system content. Assert on structure/keywords, never full-string equality.

### Success Criteria:

#### Automated Verification:

- Unit tests pass: `uv run pytest tests/test_llm.py`
- Full suite passes: `uv run pytest`
- Linting passes: `uv run ruff check .`
- Formatting clean: `uv run ruff format --check .`

#### Manual Verification:

- A manual generation of text containing specific names/numbers no longer invents extra facts.
- A creative modifier (e.g. Shakespeare, Kawaii) still transforms heavily — faithfulness did not neuter style.
- Output reliably wraps in `<body>` (and `<title>` when the template requests one).

**Implementation Note**: After this phase and all automated verification passes, pause for manual confirmation that the
faithfulness-vs-style behavior is right before proceeding.

---

## Phase 2: Parser Cascade Hardening

### Overview

Improve `parse_result()` so a response with a title but no body, or vice-versa, no longer silently loses content. Add
unit-test cases for each cascade branch.

### Changes Required:

#### 1. parse_result cascade

**File**: `core/llm.py:112-126`

**Intent**: Replace the all-or-nothing fallback with a three-tier cascade: (a) `<body>` present → use it, plus `<title>`
if present; (b) `<title>` present but no `<body>` → title from tag, body = everything after `</title>` — **but if that
trailing text is empty or whitespace-only, fall back to the whole raw string (stripped) as the body** so a
`<title>X</title>`-only response never yields a blank body; (c) no tags → whole raw string as body, empty title. Never
raise on malformed-but-present output.

**Contract**: `parse_result(raw: str) -> GenerateResult` signature unchanged. Branch (b) is the new behavior — currently
a title-without-body response drops the title and returns the raw (tags included) as body. Branch (b)'s empty-tail guard
keeps body non-blank (satisfies manual criterion 2.4 and avoids regressing the current raw-string fallback). Reuse
existing `_TITLE_RE` / `_BODY_RE`.

#### 2. Parser unit tests

**File**: `tests/test_llm.py:133-151`

**Intent**: Add cases covering the new cascade so the branches are regression-guarded.

**Contract**: Keep the three existing cases (title+body, body-only, no-tags). Add: title-present-body-absent → title
extracted and body = post-`</title>` text; **empty-tail variant** (`<title>X</title>` with no/whitespace-only trailing
text) → title extracted and body falls back to the raw string (non-blank); and confirm the no-tags fallback still
returns raw as body. Plain functions, no `@pytest.mark.django_db` needed (parser is DB-free).

### Success Criteria:

#### Automated Verification:

- Parser tests pass: `uv run pytest tests/test_llm.py -k parse_result`
- Full suite passes: `uv run pytest`
- Linting passes: `uv run ruff check .`

#### Manual Verification:

- Feeding a hand-crafted `<title>…</title>` response with no `<body>` returns a non-empty title and body.

---

## Phase 3: Fixture Template De-personalization

### Overview

Rewrite all three built-in template `base_prompt`s from persona style to output-specification style and add a "preserve
all information from the source" anchor to each. No model/schema change — fixture content only.

### Changes Required:

#### 1. Rewrite the three template base_prompts

**File**: `core/fixtures/onboarding_defaults.json:3-17`

**Intent**: Remove the "You are an experienced…/senior software engineer…" persona openers and restate each template as
a description of the desired output. Add a single "Preserve all information from the source." anchor line to each to
double-anchor the system-level faithfulness constraint at task level. Keep Jira Ticket's existing section structure
(high-level description → narrative context → TODO/acceptance-criteria bullets → out-of-scope) intact — only swap the
persona opener for an output-spec opener and add the anchor.

**Contract**: `templates[*].base_prompt` stays a non-blank string (validated by `Template.clean()`,
`core/models.py:22-25`). `generate_title` flags unchanged (Email `true`, others `false`). JSON stays valid and
`loaddata`-compatible. No new fields; option groups untouched.

### Success Criteria:

#### Automated Verification:

- Fixture is valid JSON / loads cleanly: `uv run manage.py loaddata core/fixtures/onboarding_defaults.json` against a
  scratch DB (or the existing onboarding-seed test passes: `uv run pytest -k onboarding`)
- Full suite passes: `uv run pytest`
- Linting passes: `uv run ruff check .`

#### Manual Verification:

- A fresh onboarding seed produces the three templates with no persona opener and a visible "preserve all information"
  line.
- Generating with "Professional Email" yields an email that reformats the source rather than inventing business context.

---

## Phase 4: Standalone Eval Tool

### Overview

Add `tools/eval_prompts.py`: a standalone script that runs a candidate `SYSTEM_PROMPT` variant against the current one
over a curated synthetic corpus, prints a unified diff per input, and appends a gitignored JSONL log. Model is
configurable (defaults to `OPENROUTER_MODEL`, overridable via `OPENROUTER_EVAL_MODEL`).

### Changes Required:

#### 1. Eval script

**File**: `tools/eval_prompts.py` (new)

**Intent**: Provide a repeatable before/after comparison harness. Bootstrap Django (`DJANGO_SETTINGS_MODULE`), reuse the
real `build_messages()` so the eval exercises the actual prompt-assembly path, run each corpus input through both the
current `SYSTEM_PROMPT` and a candidate variant, print a unified diff, and append results to a JSONL log.

**Contract**: Runnable as `uv run python tools/eval_prompts.py`. Reads model from `settings.OPENROUTER_MODEL`, with an
`OPENROUTER_EVAL_MODEL` env override (and/or a `--model` flag). Calls OpenRouter via the same client config as the app
(`OPENROUTER_API_KEY` / `OPENROUTER_BASE_URL`). **Pass `temperature=0` on every eval call** so the diff is attributable
to the prompt change rather than sampling noise. The before/after comparison is only meaningful when the model is pinned
to a **concrete** model (not `openrouter/auto:free`, which can route to a different underlying model per call) — print a
warning if the resolved eval model is `auto`, and document that `OPENROUTER_EVAL_MODEL` should be set to a specific
model. (N-sample repetition to average out residual noise is a possible follow-up, out of scope here.) On missing API
key, exits with a clear message rather than tracebacking. Writes `eval_log.jsonl` (gitignored). Does not write to the
DB; constructs **unsaved `Template`/`Option` model instances** (Django ORM models, not dataclasses — `core/models.py`)
after `django.setup()` to drive `build_messages()` without a DB write. (Using real model instances keeps the
`template: Template` type hint satisfied for mypy; a duck-typed stand-in would not.)

#### 2. Curated synthetic corpus

**File**: `tools/eval_prompts.py` (inline constant, or `tools/eval_corpus.py`)

**Intent**: ~6–10 synthetic inputs chosen to stress faithfulness (named people, specific numbers, dates) and to cover
each template type (email, jira, meeting notes). All synthetic — never real user data (non-retention NFR).

**Contract**: A list of `(label, base_prompt, input_text)` (or a small dataclass) covering at least: one fact-dense
input (names + numbers + dates), one terse/ambiguous input, and one input per built-in template style.

#### 3. Gitignore the eval log

**File**: `.gitignore`

**Intent**: Keep generated eval output out of version control.

**Contract**: Add `eval_log.jsonl` (and any `tools/*.jsonl` eval artifacts) to `.gitignore`.

#### 4. Document the tool

**File**: `CLAUDE.md` (Commands table) and/or `tools/` docstring

**Intent**: Make the eval workflow discoverable.

**Contract**: One row/line documenting `uv run python tools/eval_prompts.py` and the optional `OPENROUTER_EVAL_MODEL`.
Note that it needs `OPENROUTER_API_KEY` (unlike `korpo-review`).

### Success Criteria:

#### Automated Verification:

- Script imports and builds messages without a network call: `uv run python -c "import tools.eval_prompts"` (or a dry
  `--no-call` path) exits 0
- Linting passes: `uv run ruff check .`
- `eval_log.jsonl` is gitignored: `git check-ignore eval_log.jsonl` succeeds

#### Manual Verification:

- `uv run python tools/eval_prompts.py` (with `OPENROUTER_API_KEY` set) prints per-input diffs and writes the JSONL log.
- The diff makes it visibly clear when the new prompt suppresses invented content on the fact-dense inputs.
- Running with `OPENROUTER_EVAL_MODEL` set targets the chosen model.

---

## Testing Strategy

### Unit Tests:

- Prompt structure: faithfulness clause present, role phrase present, `<body>` present, `<title>` absent without title,
  `<title>` before `<body>` with title, markdown directive present, user text absent from system (Phase 1).
- Parser cascade: title+body, body-only, title-only (new), no-tags (Phase 2).
- Assert on stable keywords/structure — never full-string prompt equality (brittleness guard).

### Integration Tests:

- Existing onboarding-seed test continues to pass with the rewritten fixture (Phase 3).
- `test_generate_calls_create_with_model_and_messages` continues to pass (no signature change).

### Manual Testing Steps:

1. Generate from a fact-dense input (names, numbers, dates) — confirm no invented facts.
2. Apply a heavy-transform modifier (Shakespeare / Kawaii) — confirm style still lands.
3. Generate with a title-requesting template — confirm both tags returned and parsed.
4. Run `tools/eval_prompts.py` and read the diff + JSONL log on the corpus.

## Performance Considerations

None of consequence. The prompt grows by a few hundred tokens (faithfulness block + format example) — negligible against
the per-request cost and well within context. The eval tool makes real API calls but is a manual dev utility, not on any
hot path.

## Migration Notes

Fixture changes affect **new** onboarding seeds only; existing users' customized templates are untouched (the fixture is
a seed, not a migration). No schema change, no data migration.

## References

- Research: `context/changes/prompt-tuning/research.md`
- Prior prompt work: `context/archive/2026-06-15-improve-prompts-and-examples/plan.md`
- Original prompt architecture / injection rationale: `context/archive/2026-06-01-text-generation-flow/plan.md`
- Key code: `core/llm.py:30-47` (prompts), `core/llm.py:112-126` (parser), `core/llm.py:79-109` (`build_messages`),
  `core/fixtures/onboarding_defaults.json:3-17` (templates), `tests/test_llm.py` (tests)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: System Prompt & Output Contract

#### Automated

- [x] 1.1 Unit tests pass: `uv run pytest tests/test_llm.py` — db4ceb7
- [x] 1.2 Full suite passes: `uv run pytest` — db4ceb7
- [x] 1.3 Linting passes: `uv run ruff check .` — db4ceb7
- [x] 1.4 Formatting clean: `uv run ruff format --check .` — db4ceb7

#### Manual

- [x] 1.5 Fact-dense generation no longer invents extra facts — db4ceb7
- [x] 1.6 Creative modifier still transforms heavily (style not neutered) — db4ceb7
- [x] 1.7 Output reliably wraps in `<body>` (and `<title>` when requested) — db4ceb7

### Phase 2: Parser Cascade Hardening

#### Automated

- [x] 2.1 Parser tests pass: `uv run pytest tests/test_llm.py -k parse_result` — 0c2ee2c
- [x] 2.2 Full suite passes: `uv run pytest` — 0c2ee2c
- [x] 2.3 Linting passes: `uv run ruff check .` — 0c2ee2c

#### Manual

- [x] 2.4 Title-without-body response returns non-empty title and body — 0c2ee2c

### Phase 3: Fixture Template De-personalization

#### Automated

- [x] 3.1 Fixture loads cleanly / onboarding-seed test passes
- [x] 3.2 Full suite passes: `uv run pytest`
- [x] 3.3 Linting passes: `uv run ruff check .`

#### Manual

- [x] 3.4 Fresh seed shows no persona opener + visible preserve-information line
- [x] 3.5 "Professional Email" reformats rather than inventing business context

### Phase 4: Standalone Eval Tool

#### Automated

- [ ] 4.1 Script imports / builds messages without a network call (exit 0)
- [ ] 4.2 Linting passes: `uv run ruff check .`
- [ ] 4.3 `eval_log.jsonl` is gitignored: `git check-ignore eval_log.jsonl`

#### Manual

- [ ] 4.4 Eval run prints per-input diffs and writes the JSONL log
- [ ] 4.5 Diff visibly shows invented content suppressed on fact-dense inputs
- [ ] 4.6 `OPENROUTER_EVAL_MODEL` override targets the chosen model
