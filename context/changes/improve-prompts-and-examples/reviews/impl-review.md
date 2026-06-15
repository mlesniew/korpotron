<!-- IMPL-REVIEW-REPORT -->

# Implementation Review: Improve OpenRouter Prompting and Polish Built-in Examples

- **Plan**: context/changes/improve-prompts-and-examples/plan.md
- **Scope**: All 3 Phases
- **Date**: 2026-06-15
- **Verdict**: APPROVED (after triage fixes)
- **Findings**: 0 critical · 2 warnings · 5 observations

## Verdicts

| Dimension           | Verdict         |
| ------------------- | --------------- |
| Plan Adherence      | PASS            |
| Scope Discipline    | PASS            |
| Safety & Quality    | PASS (post-fix) |
| Architecture        | PASS            |
| Pattern Consistency | PASS (post-fix) |
| Success Criteria    | PASS            |

## Findings

### F1 — \r bypass in single-line validation

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: core/models.py:59 AND core/forms.py:21
- **Detail**: Both newline checks tested `"\n"` only. A bare `"\r"` or `"\r\n"` mid-string after strip() would pass
  validation while still being multi-line content in the LLM prompt.
- **Fix**: Changed `if "\n" in value:` to `if any(c in value for c in "\r\n"):` in both locations. Added
  `test_option_clean_raises_on_carriage_return` in test_core_models.py and
  `test_option_group_create_rejects_crlf_instruction` in test_option_group_views.py.
- **Decision**: FIXED

### F2 — {{ error }} missing |striptags in optiongroup_form.html

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: templates/core/optiongroup_form.html:46
- **Detail**: The formset.non_form_errors loop rendered `{{ error }}` without `|striptags`. Every other error display in
  this file and in sibling template_form.html uses `|striptags`.
- **Fix**: Changed to `{{ error|striptags }}` on line 46.
- **Decision**: FIXED

### F3 — \_construct_form return type annotated as object

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: core/forms.py:27
- **Detail**: Return annotation was `object` — unusually loose for a codebase that mandates type hints. Correct type is
  `forms.BaseForm`.
- **Fix**: Changed `-> object:` to `-> forms.BaseForm:`.
- **Decision**: FIXED

### F4 — Forward-reference string "User" annotation in test

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/test_llm.py:95
- **Detail**: One test function used `user: "User"` (string forward-reference) while every other test in the file used
  unquoted `User` (already imported).
- **Fix**: Removed the quotes.
- **Decision**: FIXED

### F5 — Brittle "- " substring check in no-options test

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: tests/test_llm.py:79
- **Detail**: `"- " not in block` would false-fail if base_prompt itself contained "- ".
- **Fix**: Replaced with `assert not any(line.startswith("- ") for line in block.splitlines())`.
- **Decision**: FIXED

### F6 — clean() does not reject blank-after-strip values

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/models.py:22-23, 57-58
- **Detail**: Template.clean() and Option.clean() stripped but never rejected an empty result.
- **Fix**: Added blank-after-strip ValidationError to both Template.clean() and Option.clean().
- **Decision**: FIXED

### F7 — Empty base_prompt edge case in build_messages()

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/llm.py:99
- **Detail**: Empty base_prompt would produce "\n\n- …" with no base instruction. Resolved as side effect of F6.
- **Fix**: No code change needed; F6 prevents empty base_prompt from being stored.
- **Decision**: FIXED (covered by F6)
