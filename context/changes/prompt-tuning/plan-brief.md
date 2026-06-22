# Prompt Tuning for Better Output Quality — Plan Brief

> Full plan: `context/changes/prompt-tuning/plan.md` Research: `context/changes/prompt-tuning/research.md`

## What & Why

The app's rewritten text is low quality: on lightweight OpenRouter models it acts like a generative assistant — it
invents facts, embellishes, and sometimes drops the output tags. We tune the prompt layer (system prompt, fixture
templates, parser) to constrain it to faithful style-transfer, and add an eval tool so quality changes can be measured
instead of guessed.

## Starting Point

`SYSTEM_PROMPT` (`core/llm.py:30-41`) has injection protection and a markdown directive but no faithfulness rule and a
generic "writing assistant" role. The three built-in fixture templates open with conflicting "You are an experienced…"
personas. `parse_result()` drops the title when `<body>` is missing. No eval tooling exists. `build_messages()` is a
pure function — a clean seam for a script harness.

## Desired End State

Default output preserves the source's facts, names, numbers, dates, and claims while still honoring deliberately
creative modifiers (Shakespeare, Kawaii, Korpotron Ultra). Output reliably wraps in `<body>`/`<title>` and the parser
recovers partial compliance. The three templates describe desired output rather than a persona. A developer can run
`uv run python tools/eval_prompts.py` to diff a candidate prompt variant against the current one over a synthetic
corpus.

## Key Decisions Made

| Decision             | Choice                                           | Why                                                        | Source   |
| -------------------- | ------------------------------------------------ | ---------------------------------------------------------- | -------- |
| Scope                | Prompt fixes + eval tool                         | Ship quality fixes AND a way to verify them                | Plan     |
| Faithfulness framing | Protect facts, allow style                       | Stop invention without neutering creative modifiers        | Plan     |
| Output format        | Improved XML + parser cascade                    | Prompt-only; works across all free models, no detection    | Plan     |
| Eval corpus          | Curated synthetic (~6–10)                        | Deterministic, NFR-safe, targets faithfulness failures     | Plan     |
| Eval model           | Configurable; defaults to `OPENROUTER_MODEL`     | Tests prod behavior, pinnable for comparison               | Plan     |
| Prod model lock      | Out of scope — noted as follow-up                | Keeps change focused; config has ops implications          | Plan     |
| Template rewrite     | De-persona all three + faithfulness anchor       | Uniform role; double-anchors faithfulness at task level    | Plan     |
| Testing              | Update + extend unit tests (structure + cascade) | Guards parser/clauses; eval tool covers quality separately | Plan     |
| Modifier rewrite     | Not done — already imperative/specific           | Current fixture is newer than research Section 4 described | Research |

## Scope

**In scope:** `SYSTEM_PROMPT` + `TITLE_CONTRACT` rewrite, `parse_result()` cascade, fixture template de-personalization,
`tools/eval_prompts.py` + synthetic corpus, related unit tests, gitignore + docs.

**Out of scope:** Locking production `OPENROUTER_MODEL`, JSON structured outputs, DeepEval/G-Eval scoring, a user-facing
"Faithful" modifier, any option/modifier rewrite, any schema/data migration.

## Architecture / Approach

All changes live in the existing prompt layer. The system prompt gains a facts-protecting (style-permitting)
faithfulness block, a "style-transfer editor" role, a silent-CoT anchor, and a literal `<body>` format example. The
parser becomes a three-tier cascade. Fixture templates switch from persona framing to output specification with a
per-template faithfulness anchor. The eval tool reuses the pure `build_messages()` to drive real API calls over a
synthetic corpus and emits a unified diff plus a gitignored JSONL log.

## Phases at a Glance

| Phase                          | What it delivers                                 | Key risk                                                |
| ------------------------------ | ------------------------------------------------ | ------------------------------------------------------- |
| 1. System prompt & contract    | Faithfulness + role + format example; tests      | Wording fights creative modifiers if mis-scoped         |
| 2. Parser cascade              | Partial-compliance recovery; tests               | Edge case where post-`</title>` text is empty           |
| 3. Template de-personalization | Three output-spec templates + anchors            | Breaking Jira's detailed section structure              |
| 4. Eval tool                   | `tools/eval_prompts.py` + synthetic corpus + log | Needs `OPENROUTER_API_KEY`; non-retention NFR on corpus |

**Prerequisites:** Working dev env (`uv`, `.env` with `SECRET_KEY`); `OPENROUTER_API_KEY` for Phase 4 manual runs.
**Estimated effort:** ~2–3 sessions across 4 phases; phases 1–3 are small, phase 4 is the bulk.

## Open Risks & Assumptions

- Production `OPENROUTER_MODEL` stays `openrouter/auto:free`, so output varies per request — prompt tuning is somewhat
  noisy until a later change pins a model. Recorded as a follow-up.
- The "protect facts, allow style" boundary needs careful wording so the model doesn't strip stylistic content;
  validated manually in Phase 1.
- Synthetic corpus may not perfectly mirror the real-world bad outputs that triggered this change (no captured failures
  available; non-retention NFR prevents collecting real ones).

## Success Criteria (Summary)

- Fact-dense inputs are rewritten without invented facts, while creative modifiers still visibly transform.
- Output reliably tagged; titles no longer silently dropped on partial compliance.
- `tools/eval_prompts.py` produces a readable before/after diff over the synthetic corpus.
