# Agentic Code-Review CLI (Python Claude Agent SDK) Implementation Plan

## Overview

Build a standalone, local, dev-only CLI tool that performs an automated code review of a `git diff`. The tool is the
Python port of the lesson's TypeScript `review.ts`: it reads a diff from stdin, sends it to Claude through the **Python
Claude Agent SDK** with a custom reviewer system prompt, no tools, a two-turn limit, and **native structured output**,
then prints a structured review (five 1–10 scores, a `pass`/`fail` verdict, and a Markdown summary) and gates its exit
code on the verdict.

This is an experimentation utility, intentionally decoupled from the Django app — it never imports Django and lives
outside the request path, mirroring how the app already boots without `OPENROUTER_API_KEY`.

## Current State Analysis

- `pyproject.toml` has `[project]` deps (django, openai, gunicorn, …) and a `[dependency-groups] dev` block (mypy, ruff,
  pytest, …). It has **no `[build-system]`** and **no `[project.scripts]`** — uv currently treats the project as a
  non-packaged application. `claude-agent-sdk` and `pydantic` are not present (pydantic is likely transitive via
  django/openai but not declared).
- `core/llm.py` is the existing model-call convention: a module-level client factory (`_get_client()`) that tests patch,
  a frozen dataclass result (`GenerateResult`), and a clean split between pure prompt-assembly and the network call. The
  review tool **parallels** this style (module-level `query` reference, a typed result model) but does **not** reuse it
  — it is a different provider/SDK and must not import Django (`from django.conf import settings`).
- `Dockerfile` builds prod via `uv sync --frozen --no-dev --no-install-project` (builder) and a `static-builder` stage
  via `uv sync --frozen --no-install-project` (full deps). **Both stages use `--no-install-project`**, so adding a
  `[build-system]` and `[project.scripts]` does not change Docker behavior, and a **dev-group** dependency never reaches
  the prod image (`--no-dev`).
- `.env.example` documents provider keys with commented optional lines (e.g. `OPENROUTER_MODEL`). It has no
  `ANTHROPIC_API_KEY`.
- `CLAUDE.md` has a Commands table (run server, migrate, test, lint, format) and the conventions: type hints on all new
  code, mypy, ruff format/lint, **uv** for adding packages.
- Tests live in top-level `tests/` (pytest + pytest-django). No tests are written this pass (experimentation).
- `context/changes/agentic-review/research.md` verified every SDK primitive against current docs and drafted a reference
  implementation. Its five Open Questions are the decisions this plan resolves (see Key Discoveries).

## Desired End State

A developer can run:

```
git diff | uv run python tools/review.py
```

or, after packaging:

```
git diff | uv run korpo-review
```

and get pretty-printed JSON of the review on **stdout**, a short cost/usage line on **stderr**, and an exit code of `0`
when the verdict is `pass` and non-zero when it is `fail` (or on any non-`success` SDK result). No `ANTHROPIC_API_KEY`
is required for local personal use (the SDK falls back to the Claude subscription login).

Verification: `uv sync` resolves; `uv run ruff check .` and `uv run ruff format --check .` pass; `uv run mypy tools`
passes; the tool runs end-to-end against a sample diff and returns a populated `Review`; `docker build .` succeeds.

### Key Discoveries:

- Python SDK has full parity for everything the lesson uses — `query()` async-iterator, `ClaudeAgentOptions`
  (`system_prompt`, `model`, `max_turns`, `allowed_tools`, `setting_sources`, `output_format`, `max_budget_usd`), and
  `ResultMessage.structured_output` / `.total_cost_usd` / `.usage` / `.model_usage` (`research.md:36-71`,
  `research.md:93-127`, `research.md:186-225`).
- **Schema (resolved → Pydantic single source):** define a Pydantic `Review` model; pass `Review.model_json_schema()` to
  `output_format` and validate the result with `Review.model_validate(structured_output)`. Requires
  `model_config = ConfigDict(extra="forbid")` (emits `additionalProperties: false`) and **all fields required** (no
  defaults). Numeric `minimum`/`maximum` are rejected by structured output, so the 1–10 range lives in the field
  **description** and prompt, not the schema (`research.md:132-158`).
- **Determinism levers** map to clean Python knobs: custom `system_prompt` string (avoids the `claude_code` preset and
  project memory), `setting_sources=[]` (don't load `CLAUDE.md`/`.claude`), `allowed_tools=[]` (no tools), `max_turns=2`
  (`research.md:161-183`, `research.md:360-373`).
- **Auth (resolved):** local personal use needs no key — subscription login fallback. A Console `ANTHROPIC_API_KEY` is
  only needed later for shared/CI use (`research.md:259-271`, `research.md:391-393`).
- **Packaging wrinkle:** `[project.scripts]` needs an installable package. Add a minimal hatchling `[build-system]`
  scoped to `packages = ["tools"]` so it stays isolated from the Django app; both Docker stages already use
  `--no-install-project`.
- Watch for `ResultMessage.subtype == "error_max_structured_output_retries"` — if it appears, bump `max_turns` slightly
  rather than fighting the schema (`research.md:179-183`).
- Lessons (`context/foundation/lessons.md`): **verify Docker build before committing dep changes**; **sync GitHub
  issues** after context changes.

## What We're NOT Doing

- No CI/CD wiring, GitHub Action, or PR-comment posting (that is M5L3 / later).
- No Django management command and no import of Django anywhere in the tool.
- No `ANTHROPIC_API_KEY`-based auth setup for shared/CI use (only a documented note for later).
- No tests this pass (chosen: experimentation first; the tool keeps a patchable `query` seam so tests can be added
  later).
- No read-only-tool variant (`allowed_tools=["Read","Glob","Grep"]`) — the diff is passed inline; tools stay off.
- No request to enumerate built-ins in `disallowed_tools` — `allowed_tools=[]` + `setting_sources=[]` is sufficient for
  this minimal port.

## Implementation Approach

Two phases. Phase 1 delivers the runnable tool (deps + `tools/review.py`) so it works immediately via
`uv run python tools/review.py`. Phase 2 adds the console-script ergonomics, docs, env note, and the full verification
(lint, mypy, Docker build) before commit.

The tool is a single module with a clear seam: a module-level reference to the SDK `query` (so it can be patched later),
a pure Pydantic `Review` model, an async `run_review(diff)` coroutine, and a synchronous `main()` entry point (console
scripts must call a sync function; `main()` does `asyncio.run(...)` internally and returns the exit code).

## Critical Implementation Details

- **Console-script entry must be synchronous.** `[project.scripts] korpo-review = "tools.review:main"` calls `main()`
  with no args; `main()` reads stdin, runs `asyncio.run(run_review(diff))`, prints output, and returns an `int` exit
  code (Python passes a returned int to `sys.exit`).
- **Schema config is load-bearing.** Without `ConfigDict(extra="forbid")` and all-required fields, the generated schema
  may be rejected by `output_format`. If `model_json_schema()` is still rejected at runtime (draft-2020-12 `title`
  keys), fall back to a hand-written dict identical in shape to the SDK e2e test and keep `Review` only for validation —
  this is the documented contingency, not the default path.
- **Two output streams.** JSON review → stdout (machine-readable, nothing else on it); cost/usage/diagnostics → stderr.
  Keep them separate so the stdout JSON stays clean for downstream consumers.

## Phase 1: Dependencies & the review tool

### Overview

Add the two dev dependencies and implement the runnable review module.

### Changes Required:

#### 1. Dev dependencies

**File**: `pyproject.toml`

**Intent**: Make the SDK and schema library available to the dev/CI toolchain without shipping them to the prod image.

**Contract**: Add `claude-agent-sdk` and `pydantic` to `[dependency-groups] dev` via
`uv add --dev claude-agent-sdk pydantic` (pin versions as uv resolves them). `uv.lock` updates. Requires Python ≥3.10
(repo is 3.12 — fine).

#### 2. The review module

**File**: `tools/review.py` (new) and `tools/__init__.py` (new, empty — makes `tools` an importable package)

**Intent**: Port `review.ts` to Python: read a diff, run a structured, tool-less, two-turn review through the Claude
Agent SDK, validate and return a typed `Review`, then print JSON + cost and exit on the verdict.

**Contract**:

- A module-level `from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage` and a module-level alias for
  `query` so it can be patched in future tests.
- `class Review(BaseModel)` with `model_config = ConfigDict(extra="forbid")` and **all-required** fields:
  `implementation_correctness: int`, `idiomaticity: int`, `complexity: int`, `test_risk_coverage: int`,
  `security_safety: int` (each with `Field(description=...)` carrying the "scale 1–10" rubric),
  `verdict: Literal["pass", "fail"]`, `summary: str`. No defaults on any field.
- `SYSTEM_PROMPT` constant: a precise/constructive reviewer persona scoring the five criteria 1–10 and issuing a binding
  verdict + Markdown summary (custom prompt → avoids the `claude_code` preset).
- `async def run_review(diff: str) -> Review`: builds
  `ClaudeAgentOptions(system_prompt=SYSTEM_PROMPT, model="claude-sonnet-4-6", max_turns=2, allowed_tools=[], setting_sources=[], output_format={"type":"json_schema", "schema": Review.model_json_schema()}, max_budget_usd=<const>)`;
  iterates `async for message in query(...)` capturing the `ResultMessage`; raises `RuntimeError` if none returned or
  `subtype != "success"` (include `subtype` + joined `errors`); returns
  `Review.model_validate(result.structured_output)`. The `ResultMessage` (with `total_cost_usd`, `usage`, `model_usage`)
  is kept for the caller to report cost.
- `def main() -> int`: `diff = sys.stdin.read()`; run `run_review` via `asyncio.run`; on success print indented JSON of
  the review to stdout and a one-line cost/usage summary to stderr; return `0` for `verdict == "pass"`, non-zero for
  `fail`; on `RuntimeError` print the message to stderr and return a non-zero code.
- `if __name__ == "__main__": raise SystemExit(main())` so `uv run python tools/review.py` works before packaging.
- A module-level `MAX_BUDGET_USD` constant (e.g. `0.5`) feeding `max_budget_usd` — the lesson's hard ceiling.

### Success Criteria:

#### Automated Verification:

- Dependencies resolve: `uv sync`
- Linting passes: `uv run ruff check tools`
- Formatting clean: `uv run ruff format --check tools`
- Type checking passes: `uv run mypy tools`
- Module imports without error: `uv run python -c "import tools.review"`

#### Manual Verification:

- `git diff | uv run python tools/review.py` against a real diff returns a populated `Review` (five scores, verdict,
  summary) as pretty JSON, with a cost line on stderr.
- Exit code is `0` on a `pass` verdict and non-zero on `fail` (check `echo $?`).
- Running with an empty/no diff fails cleanly with a readable stderr message, not a traceback dump.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual
confirmation that the tool runs end-to-end before proceeding to packaging.

---

## Phase 2: Packaging & docs

### Overview

Add the console-script entry point and its build-system, document usage and the optional auth key, verify the Docker
build, and flip the change status.

### Changes Required:

#### 1. Build-system + console script

**File**: `pyproject.toml`

**Intent**: Expose a `korpo-review` command without disturbing the Django app or the Docker build.

**Contract**: Add a `[build-system]` using hatchling; add `[tool.hatch.build.targets.wheel]` with `packages = ["tools"]`
to scope the package to the tool only; add `[project.scripts]` with `korpo-review = "tools.review:main"`. `uv sync` then
installs the project so the script is available via `uv run korpo-review`. (Both Docker stages use
`--no-install-project`, so the prod build is unaffected.)

#### 2. Commands documentation

**File**: `CLAUDE.md`

**Intent**: Make the review tool discoverable alongside the other project commands.

**Contract**: Add a row to the Commands table — e.g. `Review a diff` → `git diff | uv run korpo-review` — and a short
note that the tool is a standalone dev utility (not part of the app runtime) using the Claude Agent SDK, needing no key
for local personal use.

#### 3. Optional auth note

**File**: `.env.example`

**Intent**: Document the optional `ANTHROPIC_API_KEY` for future shared/CI use without implying it's required now.

**Contract**: Add a commented block (mirroring the `OPENROUTER_*` style) explaining: local personal use needs no key
(subscription login fallback); set a Console `ANTHROPIC_API_KEY` only when sharing the tool or running in CI. Keep the
line commented so nothing breaks by default.

#### 4. Change status

**File**: `context/changes/agentic-review/change.md`

**Intent**: Reflect that the change is planned and implemented.

**Contract**: Set `status: planned` (and later `implemented` per the team's flow) and `updated:` to today.

### Success Criteria:

#### Automated Verification:

- Dependencies/install resolve: `uv sync`
- Console script is wired: `uv run korpo-review < /dev/null` runs the tool (fails cleanly on empty diff, proving the
  entry point resolves)
- Linting passes: `uv run ruff check .`
- Type checking passes: `uv run mypy tools`
- Docker image builds: `docker build -t korpotron-test .` (lessons.md rule)

#### Manual Verification:

- `git diff | uv run korpo-review` produces the same result as the direct invocation from Phase 1.
- `CLAUDE.md` and `.env.example` read correctly and match the actual command/behavior.
- GitHub issue for `agentic-review` is updated/closed per lessons.md sync rule.

**Implementation Note**: After automated verification (including the Docker build) passes, pause for manual confirmation
before committing.

---

## Testing Strategy

No automated tests this pass (experimentation). The module is written with a patchable module-level `query` seam and a
pure `Review` model so tests can be added later without refactoring:

- **Future unit tests** would patch `query` to yield a fake `ResultMessage` and assert: schema generation,
  `model_validate` on `structured_output`, error-subtype branching, and `main()` exit codes — mirroring `core/llm.py`'s
  patchable-factory test pattern.

### Manual Testing Steps:

1. `git diff | uv run python tools/review.py` on a branch with real changes → populated JSON review + stderr cost line.
2. Confirm exit code: `git diff | uv run python tools/review.py; echo $?` (0 on pass, non-zero on fail).
3. Empty diff → clean stderr error, non-zero exit, no traceback.
4. After Phase 2: repeat 1–2 via `uv run korpo-review`.

## Performance Considerations

Single short-lived run per invocation; `max_turns=2` and `max_budget_usd` bound time and cost. No app-runtime impact —
the dependency is dev-only and never imported by Django.

## Migration Notes

None — additive only. The `[build-system]` addition is isolated via `packages = ["tools"]` and does not change how the
Django app runs (manage.py / gunicorn) or how Docker builds (both stages use `--no-install-project`).

## References

- Related research: `context/changes/agentic-review/research.md`
- Reference design (to port): `your-first-team-agent-sdk-costs-metrics.md:188-229`
- Existing model-call convention to parallel: `core/llm.py:64-142`
- Lessons: `context/foundation/lessons.md` (Docker build verification; GitHub issue sync)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See
> `references/progress-format.md`.

### Phase 1: Dependencies & the review tool

#### Automated

- [x] 1.1 Dependencies resolve: `uv sync` — cccc9ce
- [x] 1.2 Linting passes: `uv run ruff check tools` — cccc9ce
- [x] 1.3 Formatting clean: `uv run ruff format --check tools` — cccc9ce
- [x] 1.4 Type checking passes: `uv run mypy tools` — cccc9ce
- [x] 1.5 Module imports without error: `uv run python -c "import tools.review"` — cccc9ce

#### Manual

- [x] 1.6 `git diff | uv run python tools/review.py` returns a populated Review as pretty JSON with stderr cost line —
      cccc9ce
- [x] 1.7 Exit code is 0 on pass, non-zero on fail — cccc9ce
- [x] 1.8 Empty/no diff fails cleanly with a readable stderr message (no traceback) — cccc9ce

### Phase 2: Packaging & docs

#### Automated

- [x] 2.1 Dependencies/install resolve: `uv sync` — 2ed41fe
- [x] 2.2 Console script wired: `uv run korpo-review < /dev/null` runs the tool — 2ed41fe
- [x] 2.3 Linting passes: `uv run ruff check .` — 2ed41fe
- [x] 2.4 Type checking passes: `uv run mypy tools` — 2ed41fe
- [x] 2.5 Docker image builds: `docker build -t korpotron-test .` — 2ed41fe

#### Manual

- [x] 2.6 `git diff | uv run korpo-review` matches the Phase 1 direct invocation — 2ed41fe
- [x] 2.7 `CLAUDE.md` and `.env.example` read correctly and match actual behavior — 2ed41fe
- [x] 2.8 GitHub issue for `agentic-review` updated/closed per lessons.md sync rule — 2ed41fe
