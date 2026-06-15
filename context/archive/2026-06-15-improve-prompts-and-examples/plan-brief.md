# Improve OpenRouter Prompting and Polish Built-in Examples — Plan Brief

> Full plan: `context/changes/improve-prompts-and-examples/plan.md`

## What & Why

The prompt sent to OpenRouter is a flat newline-joined blob with no structure, no markdown instruction, and no enforced
format on modifier instructions. This change gives the prompt a clear two-part shape (template role + bullet-list
modifiers), tells the LLM to respond in markdown, enforces that modifiers are always single-line, and cleans up the
built-in fixture examples so they serve as good user-facing models.

## Starting Point

`build_messages()` in `core/llm.py:92-94` joins `base_prompt` and all selected `option.instruction` values with plain
`"\n"`. `Option.instruction` is an unconstrained `TextField` rendered as a 2-row textarea. The system prompt has no
markdown directive. The onboarding fixture has two typos and a vocabulary conflict between the "Reading complexity" and
"Corporate Buzzword Level" groups.

## Desired End State

A generation call with template + 2 modifiers produces an `<instructions>` block like:

```
You are an experienced corporate communication specialist.
Transform the text into a polished business email.
Improve structure and readability.

- Write the result in Polish
- Use natural and conversational language.
```

The system prompt always includes "Format your response using markdown." Modifier instructions cannot contain newlines —
enforced by the model `clean()`, the form `clean_instruction()`, and the UI (text input, not textarea). The fixture
examples are typo-free and cross-group non-contradictory.

## Key Decisions Made

| Decision                       | Choice                                       | Why (1 sentence)                                                                                              |
| ------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Prompt separator               | Blank line + `- ` bullets                    | Cleanest visual boundary between template role and modifier tweaks; LLMs respond well to this structure.      |
| Markdown instruction placement | Append to `SYSTEM_PROMPT`                    | Always applies without per-template action; one place to change.                                              |
| Validation layers              | Model `clean()` + form `clean_instruction()` | Defense-in-depth: forms give field-level UI errors; model catches admin and programmatic entry points.        |
| UI widget for instruction      | `<input type="text">` replacing `<textarea>` | Signals single-line intent before the user even submits.                                                      |
| Fixture conflict fix           | Strip vocabulary from "Reading complexity"   | Vocabulary belongs to "Corporate Buzzword Level"; "Reading complexity" should govern sentence structure only. |

## Scope

**In scope:**

- `SYSTEM_PROMPT` update (markdown directive)
- `build_messages()` prompt assembly rewrite
- `Option.clean()` and `Template.clean()` in `models.py`
- `OptionForm` + `clean_instruction()` / `clean_name()` in `forms.py`
- Textarea → text input swap in `optiongroup_form.html`
- Fixture: typo fixes, double-space cleanup, Reading complexity + Shakespeare rewrites
- Test updates and new test cases in `test_llm.py`, `test_core_models.py`

**Out of scope:**

- Enforcing single-line on `base_prompt` (intentionally multi-paragraph)
- Changes to generation UI, `generate_api()`, or output parsing
- Database migrations
- Changes to `TITLE_CONTRACT` or `<body>`/`<title>` tag protocol

## Architecture / Approach

Pure sequential: each phase touches one layer of the stack with no cross-phase dependencies. Phase 1 (prompt logic) can
be verified in isolation by inspecting test output. Phase 2 (validation + UI) is entirely additive to existing
form/model code. Phase 3 (fixture) is JSON editing with no code change.

## Phases at a Glance

| Phase                  | What it delivers                                                         | Key risk                                                                           |
| ---------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| 1. Prompt construction | Structured bullet-list prompt + markdown system directive; updated tests | Existing test assertions for instruction text need `- ` prefix added               |
| 2. Validation & UI     | Single-line enforcement at model + form; text input in modifier form     | `empty-option-row` template element is a second textarea occurrence — easy to miss |
| 3. Fixture polish      | Clean, conflict-free onboarding examples                                 | Reworded instructions change user-visible modifier descriptions                    |

**Prerequisites:** None — all changes are self-contained. **Estimated effort:** ~1 session across 3 phases.

## Open Risks & Assumptions

- `base_prompt` is always non-empty (enforced by Django's default `blank=False` on `ModelForm`); otherwise the
  blank-line separator would produce a malformed leading `\n\n`.
- Existing users with multi-line modifier instructions in their database will not be retroactively validated; they will
  continue to work but would fail if re-saved through the form.

## Success Criteria (Summary)

- Generated `<instructions>` block has blank line + `- ` bullets when modifiers selected; plain `base_prompt` only when
  none.
- Attempting to save a multi-line modifier instruction shows a field-level error in the UI.
- All fixture typos fixed and modifier instructions across groups are semantically compatible.
