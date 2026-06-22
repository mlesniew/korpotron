<!-- IMPL-REVIEW-REPORT -->

# Implementation Review: Prompt Tuning for Better Output Quality

- **Plan**: context/changes/prompt-tuning/plan.md
- **Scope**: All 4 phases (full plan)
- **Date**: 2026-06-22
- **Verdict**: APPROVED
- **Findings**: 0 critical, 1 warning, 1 observation

## Verdicts

| Dimension           | Verdict |
| ------------------- | ------- |
| Plan Adherence      | PASS    |
| Scope Discipline    | PASS    |
| Safety & Quality    | PASS    |
| Architecture        | PASS    |
| Pattern Consistency | WARNING |
| Success Criteria    | PASS    |

Automated criteria all green: `pytest` 79 passed · `ruff check` clean · `ruff format --check` clean · onboarding seed 4
passed · `git check-ignore eval_log.jsonl` ignored · import + `--dry-run` exit 0 (no network) · mypy on eval tool clean.

Verified beyond checkboxes: every phase matches plan intent; all three plan-review findings (temperature=0, empty-tail
fallback, real unsaved `Template` instances) carried into code; `build_messages` reads `SYSTEM_PROMPT` as a call-time
module global (`core/llm.py:104`) so the eval tool's `_patched_system_prompt` monkeypatch genuinely flows the candidate
through the real path; non-retention NFR honored (synthetic corpus only, gitignored log); "What We're NOT Doing"
boundaries all respected; no new deps so Docker build unaffected.

## Findings

### F1 — Unparameterized `list` type hints in eval tool helpers

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tools/eval_prompts.py:174, 189
- **Detail**: `_build_for(...) -> list` and `_call(model, messages: list)` use bare `list` (i.e. `list[Any]`) rather
  than the element-typed form. The rest of the file is precisely typed, and CLAUDE.md mandates "type hints to all new
  code." mypy passes only because bare `list` degrades to `Any`, silently defeating checking on the messages list that
  `build_messages` returns as `list[ChatCompletionMessageParam]`.
- **Fix**: Annotate both as `list[ChatCompletionMessageParam]` (import the alias from `openai.types.chat`, as
  `core/llm.py` already does), or the lighter `list[dict[str, str]]` to avoid the import.
- **Decision**: FIXED (annotated both helpers with `list[ChatCompletionMessageParam]` + added the import; ruff + mypy
  clean)

### F2 — Plan named a `--no-call` flag; tool ships `--dry-run`

- **Severity**: 🔭 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: tools/eval_prompts.py:243 (criterion 4.1)
- **Detail**: Plan criterion 4.1 offered "a dry `--no-call` path" as an alternative to the bare import for no-network
  verification. The implementation named it `--dry-run` — a clearer name, and the primary import form the criterion
  specified works regardless. No behavioral gap; plan text and flag name simply diverge.
- **Fix**: None needed — `--dry-run` is the better name. Optionally update the plan's 4.1 wording for accuracy.
- **Decision**: FIXED (updated plan criterion 4.1 wording to reference `--dry-run`)
