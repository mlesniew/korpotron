<!-- PLAN-REVIEW-REPORT -->

# Plan Review: Prompt Tuning for Better Output Quality

- **Plan**: context/changes/prompt-tuning/plan.md
- **Mode**: Deep
- **Date**: 2026-06-22
- **Verdict**: REVISE → SOUND (all findings fixed 2026-06-22)
- **Findings**: 0 critical, 2 warnings, 1 observation

## Verdicts

| Dimension             | Verdict |
| --------------------- | ------- |
| End-State Alignment   | WARNING |
| Lean Execution        | PASS    |
| Architectural Fitness | PASS    |
| Blind Spots           | WARNING |
| Plan Completeness     | WARNING |

## Grounding

6/6 paths ✓, line refs ✓ (SYSTEM_PROMPT 30-41, TITLE_CONTRACT 44-47, parse_result 112-126, build_messages 79-109,
fixtures templates 3-17), `tools` is a package (`tools/__init__.py` present, so `import tools.eval_prompts` is
feasible), Progress↔Phase mechanically consistent (one `## Progress`, every phase + every criterion has a matching
`- [ ]` item), brief↔plan consistent. Plan correctly overrides stale research re: modifiers.

## Findings

### F1 — Eval tool diffs single noisy samples; may show no signal

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: End-State Alignment / Blind Spots
- **Location**: Phase 4 — Standalone Eval Tool (success criterion 4.5)
- **Detail**: Phase 4's purpose is to verify quality changes before/after instead of spot-checking the UI. But the
  design runs each corpus input once through the current prompt and once through the candidate, then diffs. The default
  model is `openrouter/auto:free`, which is non-deterministic and can route to a _different underlying model_ per call.
  A single-sample-vs-single-sample diff mixes the prompt-change effect with model/sampling noise, so criterion 4.5
  ("visibly shows invented content suppressed") may not reproducibly hold — undermining the phase's reason to exist. The
  plan exposes `OPENROUTER_EVAL_MODEL` (pins the model, good) but says nothing about temperature or sample count.
- **Fix**: In the Phase 4 contract, pin determinism for the eval path: pass `temperature=0` and document that meaningful
  comparison requires `OPENROUTER_EVAL_MODEL` set to a concrete model (not `auto`). Optionally note N-sample repetition
  as a follow-up.
  - Strength: Cheap (one kwarg + a doc line); makes the diff attributable to the prompt, which is the whole point.
  - Tradeoff: temperature=0 differs from prod's default sampling, so the eval is a controlled proxy, not prod-identical.
  - Confidence: HIGH — noise on `auto:free` is already an acknowledged open risk in the brief; this addresses it
    directly.
  - Blind spot: Not all free models honor temperature=0 identically.
- **Decision**: FIXED (Fix in plan)

### F2 — parse_result branch (b): empty body when title has no trailing text

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness / Blind Spots
- **Location**: Phase 2 — Parser Cascade (branch b)
- **Detail**: Branch (b) is "title present, no `<body>` → title from tag, body = everything after `</title>`." If the
  model emits `<title>X</title>` with nothing (or only whitespace) after it, body becomes "". That (a) contradicts
  manual criterion 2.4, which asserts a "non-empty title AND body"; and (b) is a regression vs. today's fallback, which
  returns the raw string (so the user at least sees the title text rather than a blank body). The brief names this exact
  edge ("post-`</title>` text is empty") but the Phase 2 contract doesn't resolve it.
- **Fix**: Specify the fallback in branch (b): if post-`</title>` text is blank, fall back to the whole raw string
  (stripped) as body. State this in the contract and add a unit case for the empty-tail variant.
- **Decision**: FIXED (Fix in plan)

### F3 — Template/Option called "dataclass models"; they're Django ORM models

- **Severity**: 🔭 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 4 — change #1 contract ("real dataclass models for Template/Option")
- **Detail**: `Template` and `Option` are `django.db.models.Model` subclasses (core/models.py:6,44), not dataclasses,
  and `build_messages` is typed `template: Template`. Knock-ons for the implementer: (1) construct _unsaved Django
  instances_ after `django.setup()` — no DB write needed, but the ORM must be loaded; (2) a duck-typed "stand-in" would
  satisfy the runtime but break the `Template`/`Option` type hints, and CLAUDE.md mandates mypy-clean typed code.
- **Fix**: Reword the contract to "construct unsaved Template/Option model instances (no DB write) after Django setup"
  and drop "dataclass".
- **Decision**: FIXED (Fix in plan)
