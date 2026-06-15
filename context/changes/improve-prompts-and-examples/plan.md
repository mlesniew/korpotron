# Improve OpenRouter Prompting and Polish Built-in Examples — Implementation Plan

## Overview

Harden the text-generation pipeline end-to-end: update `SYSTEM_PROMPT` to request markdown output, restructure
`build_messages()` to produce `base_prompt` + blank line + bullet-list of selected modifier instructions, enforce
single-line + trimmed constraints on modifier instructions at both model and form layer, change the instruction textarea
to a text input in the modifier UI, and fix typos and cross-group semantic conflicts in the onboarding fixture.

## Current State Analysis

`build_messages()` in `core/llm.py:92-94` flat-joins `base_prompt` and all option instructions with `"\n"` — no bullet
structure, no markdown hint in the system prompt. The `Option.instruction` field is a `TextField` (unlimited, any
whitespace) rendered as a 2-row textarea in `optiongroup_form.html:68-74` and in the `empty-option-row` template element
at line 98. No `clean()` or validators exist on any model. The onboarding fixture has two typos ("User professional" →
"Use professional", "reassurence" → "reassurance") and a semantic conflict between the "Reading complexity" and
"Corporate Buzzword Level" groups — both touch vocabulary, allowing contradictory combined instructions (e.g. "Simple" +
"Korpotron Ultra"). The "Shakespeare" instruction specifies "English", conflicting with the Language modifier group.

## Desired End State

When a user generates text with a template + modifiers selected:

1. The system prompt instructs the LLM to format its output using markdown.
2. The `<instructions>` block begins with the template's `base_prompt` (stripped), followed by a blank line, followed by
   a bullet list of selected modifier instructions (each single-line, stripped, prefixed with `- `). When no modifiers
   are selected, only the `base_prompt` appears — no blank line, no bullets.
3. Modifier instructions are guaranteed single-line at both model-validation and form-validation level, and the UI uses
   a text input (not textarea).
4. The fixture examples are clean, typo-free, and cross-group instructions are non-contradictory.

### Key Discoveries

- `llm.py:92-94` is the sole prompt-assembly point; the change is surgical.
- `forms.py` uses `RequiredOptionInlineFormSet` with a formset-level `clean()` — the right place for cross-form
  validation; individual field strip + validation needs a new custom `OptionForm` class.
- `optiongroup_form.html` has the instruction textarea in **two** places: rendered rows (line 68) and the
  `empty-option-row` `<template>` element (line 98) — both must be updated.
- `test_llm.py:63-67` asserts exact string presence and ordering for option instructions — needs updating for the `- `
  bullet prefix.
- "Reading complexity: Simple" says "Use simple vocabulary", conflicting with "Corporate Buzzword Level:
  Enterprise/Korpotron Ultra". Fix: strip vocabulary from "Reading complexity" instructions; vocabulary ownership
  belongs to "Corporate Buzzword Level".
- "Shakespeare" (Reading complexity) specifies "in elevated, Shakespeare-inspired English" — contradicts Language:
  Polish/German when both are selected. Fix: remove the "English" qualifier.

## What We're NOT Doing

- No database migrations (no model field additions or changes, only `clean()` methods).
- No changes to `TITLE_CONTRACT` or the `<body>`/`<title>` tag protocol.
- No enforcement that `base_prompt` is single-line — it is intentionally multi-paragraph.
- No changes to the generation UI or `generate_api()` view.
- No UI changes beyond the instruction textarea → input swap.

## Implementation Approach

Sequential single-layer changes: `llm.py` → `models.py` + `forms.py` → HTML template → fixture → tests verify each
phase.

---

## Phase 1: Prompt construction and system prompt

### Overview

Append the markdown formatting instruction to `SYSTEM_PROMPT` and rewrite `build_messages()` to produce the blank-line +
bullet-list format when modifiers are selected. Update `test_llm.py` to match the new format and add coverage for edge
cases.

### Changes Required:

#### 1. Update SYSTEM_PROMPT

**File**: `core/llm.py`

**Intent**: Append a markdown formatting directive to `SYSTEM_PROMPT` so the LLM consistently applies markdown to its
output regardless of which template or modifiers are used.

**Contract**: Append `"\n\nFormat your response using markdown."` to the `SYSTEM_PROMPT` string constant (lines 30-40),
after the `<body>...</body>` sentence. `TITLE_CONTRACT` is concatenated at call time and is unaffected.

#### 2. Rewrite build_messages() prompt assembly

**File**: `core/llm.py`

**Intent**: Replace the flat newline-join with logic that cleanly separates the template role (`base_prompt`) from the
modifier tweaks (bullet list), using a blank line as the visual boundary.

**Contract**: Replace lines 92-94 with:

```python
base = template.base_prompt.strip()
bullet_lines = [f"- {opt.instruction.strip()}" for opt in selected_options if opt.instruction.strip()]
instructions = (base + "\n\n" + "\n".join(bullet_lines)) if bullet_lines else base
```

When no options are selected, `instructions` is just the stripped `base_prompt`.

#### 3. Update test_llm.py

**File**: `tests/test_llm.py`

**Intent**: Update the existing message-structure test for the bullet format, and add three focused cases: (a) no
options selected → plain base_prompt with no blank line or bullet prefix; (b) options selected → blank line before first
bullet and `- ` prefix on each; (c) whitespace in base_prompt or option instruction is stripped before use.

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_llm.py` — all tests pass (including updated and new tests)
- `uv run ruff check core/llm.py tests/test_llm.py`

#### Manual Verification:

- Generate a document with a template + 2 modifiers and confirm the `<instructions>` block in the API call contains the
  blank line + bullet list.
- Generate with a template and no modifiers; confirm no blank line or `- ` prefix appears.

**Implementation Note**: After this phase passes automated verification, pause for manual confirmation before
proceeding.

---

## Phase 2: Validation and UI

### Overview

Add `clean()` to `Option` and `Template` in `models.py` for defense-in-depth. Add a custom `OptionForm` class to
`forms.py` with field-level `clean_instruction()` / `clean_name()` methods, and wire it into the formset factory. Swap
the instruction `<textarea>` to `<input type="text">` in both locations in the HTML template.

### Changes Required:

#### 1. Add clean() to Option model

**File**: `core/models.py`

**Intent**: Strip whitespace and reject newlines in `instruction` at the model layer, catching any entry point that
bypasses the form (Django admin, management commands, future API).

**Contract**: Add a `clean()` method to the `Option` class. Strip `self.instruction`, then raise
`ValidationError({"instruction": "Modifier instructions must be a single line."})` if `"\n"` remains. Also add type
annotation `def clean(self) -> None`.

#### 2. Add clean() to Template model

**File**: `core/models.py`

**Intent**: Strip leading/trailing whitespace from `base_prompt` at model level to prevent invisible whitespace from
entering stored prompts.

**Contract**: Add `def clean(self) -> None` to `Template` that sets `self.base_prompt = self.base_prompt.strip()`.

#### 3. Add custom OptionForm with field-level clean methods

**File**: `core/forms.py`

**Intent**: Provide per-field strip + single-line validation at the form layer so the UI displays a field-level error
(not just a formset banner) and cleaned data already carries stripped values.

**Contract**: Define a new `class OptionForm(forms.ModelForm)` before `RequiredOptionInlineFormSet`. It needs:

- `clean_name(self) -> str`: return `self.cleaned_data["name"].strip()`
- `clean_instruction(self) -> str`: strip the value; if `"\n"` present, raise
  `ValidationError("Modifier instructions must be a single line.")`; return stripped value.
- `class Meta`: `model = Option`, `fields = ["name", "instruction"]`

Update `OptionFormSet = inlineformset_factory(...)` to pass `form=OptionForm`.

Add `import forms` from django.forms at the top (or adjust the existing import).

#### 4. Change instruction textarea to text input

**File**: `templates/core/optiongroup_form.html`

**Intent**: Replace the 2-row textarea for the instruction field with `<input type="text">` in both the rendered option
rows and the `empty-option-row` `<template>` element, so users understand single-line input is expected before they try
to paste multi-line text.

**Contract**: Replace the `<textarea class="k-opt-instr" ...>{{ ... }}</textarea>` at lines 68-74 with:

```html
<input
  type="text"
  class="k-opt-instr"
  name="{{ option_form.instruction.html_name }}"
  id="{{ option_form.instruction.id_for_label }}"
  value="{{ option_form.instruction.value|default:'' }}"
  placeholder="Describe how this option changes the output…"
/>
```

Replace the identical textarea at lines 98-102 in the `<template id="empty-option-row">` with the same pattern but
without a `value` attribute (empty form row).

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_core_models.py tests/test_option_group_views.py` — all tests pass
- `uv run ruff check core/models.py core/forms.py`

#### Manual Verification:

- Open the modifier create/edit form; confirm the instruction field is a single-line text input.
- Attempt to submit a modifier with a multi-line instruction (paste via dev tools or programmatic POST); confirm a
  field-level validation error is shown.
- Save a modifier with trailing whitespace in the instruction; confirm stored value is stripped.
- Add a new option row dynamically (click "+ Add option"); confirm the new row also shows a text input, not a textarea.

**Implementation Note**: After this phase passes automated verification, pause for manual confirmation before
proceeding.

---

## Phase 3: Fixture polish

### Overview

Fix two typos, remove double-space padding, and rewrite "Reading complexity" instructions to eliminate semantic overlap
with "Corporate Buzzword Level". Remove the "English" qualifier from "Shakespeare" to avoid conflicting with the
Language modifier group. Verify all instructions pass the new single-line constraint.

### Changes Required:

#### 1. Fix typos and double-space padding

**File**: `core/fixtures/onboarding_defaults.json`

**Intent**: Fix `"User professional business language."` → `"Use professional business language."` in Tone >
Professional, `"reassurence"` → `"reassurance"` in Audience > Customer, and remove double-space padding (`"  "` → `" "`)
throughout all `instruction` and `base_prompt` fields.

#### 2. Rewrite "Reading complexity" instructions

**File**: `core/fixtures/onboarding_defaults.json`

**Intent**: Remove vocabulary-level guidance from the "Reading complexity" group so its instructions no longer conflict
with "Corporate Buzzword Level" when both groups are active. Vocabulary ownership stays with "Corporate Buzzword Level";
"Reading complexity" governs sentence structure, density, and text rhythm.

**Contract** — revised instructions:

- **Simple**:
  `"Use short sentences and short paragraphs. Prefer bullet points over prose where possible. Avoid complex sentence structures."`
- **Advanced**:
  `"Use varied sentence structure. Include subordinate clauses and parallel constructions where appropriate."`
- **Executive**: `"Write with economy of language. Lead with the conclusion. Avoid repetition and padding."`
- **Shakespeare**:
  `"Rewrite the text in elevated, Shakespearean style. Use archaic vocabulary and dramatic phrasing. Remain comprehensible but delightfully theatrical."`
  — "English" qualifier removed.

### Success Criteria:

#### Automated Verification:

- `python -m json.tool core/fixtures/onboarding_defaults.json > /dev/null` — valid JSON
- `uv run pytest tests/test_onboarding.py` — onboarding seeding tests pass

#### Manual Verification:

- Run `uv run manage.py loaddata core/fixtures/onboarding_defaults.json` on a clean DB; verify no errors.
- Create a fresh user account; confirm onboarding seeds the updated templates and modifiers correctly.
- Spot-check that "Reading complexity: Simple" + "Corporate Buzzword Level: Enterprise" no longer yield contradictory
  instructions.

**Implementation Note**: After this phase passes automated verification, pause for manual confirmation before
proceeding.

---

## Testing Strategy

### Unit Tests:

- `tests/test_llm.py`: bullet-list format when options present; plain base_prompt when no options; whitespace trimming
  applied in `build_messages()`; markdown hint present in system prompt.
- `tests/test_core_models.py`: `Option.clean()` strips instruction and raises on newline; `Template.clean()` strips
  base_prompt.

### Integration Tests:

- `tests/test_option_group_views.py`: POST with multi-line instruction returns form error; POST with trailing whitespace
  saves stripped value.

### Manual Testing Steps:

1. Generate with template + 2 modifiers → `<instructions>` block shows blank line + `- ` bullets.
2. Generate with template + 0 modifiers → no blank line, no `- ` prefix.
3. Create modifier with `\n` in instruction (via dev tools) → validation error, not saved.
4. Confirm rendered output displays markdown (headers, bullets visible in the browser result).

## Migration Notes

No migrations needed. `clean()` methods on models affect only validation, not the schema.

## References

- `core/llm.py:30-40` — SYSTEM_PROMPT constant
- `core/llm.py:92-94` — flat join to replace
- `core/forms.py:30-37` — OptionFormSet factory to update
- `templates/core/optiongroup_form.html:68-74, 98-102` — textarea occurrences to replace
- `core/fixtures/onboarding_defaults.json` — fixture to polish
- `tests/test_llm.py:53-67` — test requiring update for bullet format

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See
> `references/progress-format.md`.

### Phase 1: Prompt construction and system prompt

#### Automated

- [x] 1.1 `uv run pytest tests/test_llm.py` — all tests pass — 6d38310
- [x] 1.2 `uv run ruff check core/llm.py tests/test_llm.py` — 6d38310

#### Manual

- [x] 1.3 Generated `<instructions>` block shows blank line + bullets with modifiers selected — 6d38310
- [x] 1.4 No blank line or bullet prefix when no modifiers selected — 6d38310

### Phase 2: Validation and UI

#### Automated

- [x] 2.1 `uv run pytest tests/test_core_models.py tests/test_option_group_views.py` — e6cdf90
- [x] 2.2 `uv run ruff check core/models.py core/forms.py` — e6cdf90

#### Manual

- [x] 2.3 Modifier form shows single-line text input for instruction — e6cdf90
- [x] 2.4 Multi-line instruction submission returns a field-level validation error — e6cdf90
- [x] 2.5 Trailing-whitespace instruction saves as stripped value — e6cdf90
- [x] 2.6 Dynamically added option row also shows text input — e6cdf90

### Phase 3: Fixture polish

#### Automated

- [x] 3.1 `python -m json.tool core/fixtures/onboarding_defaults.json > /dev/null` — valid JSON — a4961c3
- [x] 3.2 `uv run pytest tests/test_onboarding.py` — a4961c3

#### Manual

- [x] 3.3 Fresh user sees updated fixture content after onboarding — a4961c3
- [x] 3.4 "Simple" + "Enterprise" modifiers no longer produce contradictory instructions — a4961c3
