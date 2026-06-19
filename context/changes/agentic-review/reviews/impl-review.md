<!-- IMPL-REVIEW-REPORT -->

# Implementation Review: Agentic Code-Review CLI (Python Claude Agent SDK)

- **Plan**: context/changes/agentic-review/plan.md
- **Scope**: Phases 1–2 of 2 (full plan)
- **Date**: 2026-06-19
- **Verdict**: APPROVED (with 2 low-impact warnings to clean up)
- **Findings**: 0 critical, 2 warnings, 1 observation

## Verdicts

| Dimension           | Verdict |
| ------------------- | ------- |
| Plan Adherence      | PASS    |
| Scope Discipline    | PASS    |
| Safety & Quality    | PASS    |
| Architecture        | PASS    |
| Pattern Consistency | WARNING |
| Success Criteria    | WARNING |

Verification run live during review: `uv sync`, `uv run ruff check .`, `uv run ruff format --check tools`,
`uv run mypy tools`, `import tools.review`, empty-diff clean exit (2), and `docker build -t korpotron-test .` — all
green. The tool is a faithful, well-typed port (custom system prompt, `setting_sources=[]`, `allowed_tools=[]`,
`max_turns=2`, Pydantic schema with `extra="forbid"` + all-required fields, `MAX_BUDGET_USD` ceiling, clean
stdout/stderr split, no Django import, isolated hatchling package). Both warnings are docs/process hygiene, not code
defects.

## Findings

### F1 — Manual criterion 2.8 rubber-stamped: no GitHub issue exists

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: context/changes/agentic-review/plan.md:322
- **Detail**: Checkbox 2.8 is marked `[x]` "GitHub issue for agentic-review updated/closed per lessons.md sync rule",
  but `gh issue list --state all` shows no issue referencing agentic-review (issues 1–18 are all S-/F-/Q- items). The
  lessons.md rule "Sync GitHub issues with context changes" (Applies to: impl-review) was not satisfied, and the
  checkbox claims otherwise.
- **Fix**: Either create + close a tracking issue for agentic-review, or — if an experimentation branch doesn't warrant
  one — change 2.8 to reflect that decision instead of claiming sync was done.
- **Decision**: FIXED — updated 2.8 to reflect that no issue was created; experimentation branch does not warrant one.

### F2 — CLAUDE.md Commands table is malformed

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: CLAUDE.md:36-42
- **Detail**: The "Review a diff" row contains an unescaped pipe in the command `git diff | uv run korpo-review`. In GFM
  the `|` splits the cell, so the row renders as three columns and the backtick code span breaks across cells. The
  separator row was widened to 3 columns to compensate, but the other 6 rows have only 2 cells — the table renders
  inconsistently. This also falsifies manual checkbox 2.7 ("CLAUDE.md reads correctly").
- **Fix**: Escape the pipe and restore the 2-column separator: `| Review a diff | \`git diff \| uv run korpo-review\` |`
- **Decision**: FIXED — escaped the pipe (`\|`) in CLAUDE.md and restored the 2-column separator.

### F3 — run_review returns a tuple, not the plan's literal `-> Review`

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: tools/review.py:63
- **Detail**: Plan contract writes `async def run_review(diff: str) -> Review`, but the implementation returns
  `tuple[Review, ResultMessage]`. This is benign — the same contract paragraph says the ResultMessage "is kept for the
  caller to report cost," and a tuple return is the cleanest way to honor that. Intent matches; only the literal
  signature differs. No action needed unless you want the plan text to match the code.
- **Decision**: FIXED — updated plan contract to `-> tuple[Review, ResultMessage]` to match actual implementation.
