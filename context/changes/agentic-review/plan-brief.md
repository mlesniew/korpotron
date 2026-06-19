# Agentic Code-Review CLI (Python Claude Agent SDK) — Plan Brief

> Full plan: `context/changes/agentic-review/plan.md` Research: `context/changes/agentic-review/research.md`

## What & Why

Build a standalone, local CLI that automatically reviews a `git diff` using the **Python Claude Agent SDK** — the Python
port of the lesson's TypeScript `review.ts`. It gives the repo a fast, scriptable "second pair of eyes" on changes
before commit/PR, with structured, machine-readable output.

## Starting Point

The repo is a Django 6 app on uv/Python 3.12. `core/llm.py` already establishes the model-call convention (patchable
client factory, typed result, pure prompt-assembly). `pyproject.toml` has a dev dependency group but **no
`[build-system]`/`[project.scripts]`**, and neither `claude-agent-sdk` nor `pydantic` is declared. Research has already
verified the entire Python SDK surface against current docs and drafted a reference implementation.

## Desired End State

A developer runs `git diff | uv run python tools/review.py` (or `git diff | uv run korpo-review`) and gets pretty JSON
of the review on stdout (five 1–10 scores, `pass`/`fail` verdict, Markdown summary), a cost/usage line on stderr, and an
exit code that is `0` on pass and non-zero on fail. No API key is needed for local personal use.

## Key Decisions Made

| Decision        | Choice                                          | Why (1 sentence)                                                                                                             | Source   |
| --------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------- |
| Output schema   | Pydantic as single source of truth              | `model_json_schema()` feeds `output_format`; `model_validate()` types the result — zod's exact role, matches mypy convention | Plan     |
| Placement / dep | `tools/` dir, dev-group dependency              | Clearly a dev/CI utility; `--no-dev` keeps the heavy Node-bundling SDK out of the prod image                                 | Plan     |
| Invocation      | Console-script `korpo-review`                   | Nicer ergonomics; needs a minimal hatchling build-system scoped to `packages=["tools"]`                                      | Plan     |
| Output + exit   | JSON to stdout, cost to stderr, exit on verdict | Human-readable + CI-ready gating without polluting the stdout JSON                                                           | Plan     |
| Tests           | Skipped this pass                               | Experimentation first; module keeps a patchable `query` seam for later tests                                                 | Plan     |
| Auth            | Subscription login, no key locally              | Local personal use draws from the Claude subscription; Console key only for CI/shared later                                  | Research |

## Scope

**In scope:** the `tools/review.py` module (Pydantic `Review`, async SDK call, JSON+cost output, verdict→exit-code);
dev-group deps; console-script packaging; CLAUDE.md + `.env.example` docs; Docker-build verification.

**Out of scope:** CI/GitHub Action, PR-comment posting, Django management command, `ANTHROPIC_API_KEY` setup, tests,
read-only-tool variant.

## Architecture / Approach

One self-contained module, no Django import. Module-level `query` reference (patchable seam) → `ClaudeAgentOptions`
(custom `system_prompt`, `model="claude-sonnet-4-6"`, `max_turns=2`, `allowed_tools=[]`, `setting_sources=[]`,
`output_format` from the Pydantic schema, `max_budget_usd` cap) → `async for message in query(...)` capturing the
`ResultMessage` → `Review.model_validate(structured_output)`. A synchronous `main()` wraps `asyncio.run(...)` (required
for a console-script entry) and owns stdout/stderr split + exit code.

## Phases at a Glance

| Phase                      | What it delivers                                                  | Key risk                                                                  |
| -------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1. Dependencies & the tool | Runnable `tools/review.py` via `uv run python tools/review.py`    | `model_json_schema()` dict rejected by `output_format` (draft/title keys) |
| 2. Packaging & docs        | `korpo-review` console script, docs, Docker-verified, status flip | Build-system addition perturbing the Django app / Docker build            |

**Prerequisites:** uv environment; a Claude subscription logged into Claude Code (no key) for the manual run.
**Estimated effort:** ~1 session across 2 phases.

## Open Risks & Assumptions

- Pydantic `model_json_schema()` (draft-2020-12, `title` keys, `extra="forbid"`) is accepted by `output_format` as-is.
  Contingency: hand-written dict schema, Pydantic kept for validation only.
- `error_max_structured_output_retries` subtype may appear; mitigation is a small `max_turns` bump.
- Assumes the installed `claude-agent-sdk` version bundles the Claude Code CLI (no separate Node install); pin the
  version.

## Success Criteria (Summary)

- `git diff | uv run korpo-review` returns a populated structured review and exits 0 on pass / non-zero on fail.
- The tool never imports Django and the dev-only dependency stays out of the prod Docker image (`docker build` passes).
- Lint, mypy, and `uv sync` all pass; GitHub issue synced per lessons.md.
