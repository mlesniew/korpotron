---
date: 2026-06-19T10:52:53+02:00
researcher: Michał Leśniewski
git_commit: 7969d115850bb526dbef0570bd31cead19acd495
branch: master
repository: korpotron
topic:
  "Implementing the agentic code-review tool with the Python Claude Agent SDK (port of the TypeScript + zod lesson)"
tags: [research, agentic-review, claude-agent-sdk, python, structured-output, pydantic]
status: complete
last_updated: 2026-06-19
last_updated_by: Michał Leśniewski
---

# Research: Implementing the agentic code-review tool with the Python Claude Agent SDK

**Date**: 2026-06-19T10:52:53+02:00 **Researcher**: Michał Leśniewski **Git Commit**:
7969d115850bb526dbef0570bd31cead19acd495 **Branch**: master **Repository**: korpotron

## Research Question

The lesson `your-first-team-agent-sdk-costs-metrics.md` (M5L2) shows how to build a minimal, local, scripted code-review
agent. It presents several SDKs and implements the "ready-made agent" path with the **TypeScript** Claude Agent SDK plus
**zod** for the output schema. We want to build the same tool in **Python** using the **Python Claude Agent SDK**
(https://code.claude.com/docs/en/agent-sdk/overview).

How is the lesson's `review.ts` done in Python? What replaces zod? Does the Python SDK have the same structured-output,
cost, and turn-limit primitives?

**Scope (confirmed with user):** Local CLI only — the Python equivalent of `review.ts`, run with `git diff | <script>`.
No CI/CD or Django-management-command wiring in this pass. Deliverable emphasises a concrete, runnable Python design
verified against current SDK docs.

## Summary

**The Python Claude Agent SDK is at full feature parity with the TypeScript SDK for everything the lesson uses.** Every
primitive the lesson relies on has a direct, verified Python equivalent:

| Lesson (TypeScript)                                                  | Python Claude Agent SDK                                                          |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `import { query } from "@anthropic-ai/claude-agent-sdk"`             | `from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage`          |
| `query({ prompt, options })` → `for await (const message of result)` | `async for message in query(prompt=..., options=...)`                            |
| `options.systemPrompt`                                               | `ClaudeAgentOptions(system_prompt=...)`                                          |
| `options.model: "claude-sonnet-4-6"`                                 | `model="claude-sonnet-4-6"` (or alias `"sonnet"`)                                |
| `options.maxTurns: 2`                                                | `max_turns=2`                                                                    |
| `options.tools: []` (disable tools)                                  | `allowed_tools=[]` + `setting_sources=[]` (see §Tooling)                         |
| `outputFormat: { type: "json_schema", schema }`                      | `output_format={"type": "json_schema", "schema": {...}}`                         |
| `message.structured_output`                                          | `result_message.structured_output`                                               |
| `message.usage.input_tokens`                                         | `result_message.usage["input_tokens"]`                                           |
| `message.total_cost_usd`                                             | `result_message.total_cost_usd`                                                  |
| `message.modelUsage`                                                 | `result_message.model_usage`                                                     |
| `maxBudgetUsd: 0.5` (hard cap)                                       | `max_budget_usd=0.5`                                                             |
| **zod** `z.object(...)` + `z.toJSONSchema(..., {target:"draft-07"})` | **Pydantic** model + `Model.model_json_schema()` — or a hand-written dict schema |

**The one genuine difference is the schema library.** TypeScript uses zod and converts it to JSON Schema with
`z.toJSONSchema()`. Python's `output_format` wants a **plain JSON-Schema `dict`**, so you either (a) write the dict
literally (this is exactly what the SDK's own e2e tests do — lowest risk), or (b) use **Pydantic** as the zod-equivalent
single source of truth and derive the dict via `model_json_schema()`, then validate `structured_output` with
`Model.model_validate()`.

Two operational caveats worth flagging up front:

- **CLI bundling:** recent Python SDK versions bundle the Claude Code CLI with the pip package, so no separate Node
  install is needed (older versions required Node + the CLI). Pin the version.
- **Auth for local use:** the lesson's "use my Claude subscription session without a key" trick **works for our case**.
  If you log in to Claude Code with your Claude Pro/Max subscription and set no `ANTHROPIC_API_KEY`, the SDK falls back
  to those credentials and draws from your subscription (no separate API billing). **This is fine only for local,
  personal CLI use.** The moment this tool is shared, offered to others, or runs in CI/CD, switch to a Console
  `ANTHROPIC_API_KEY` — the subscription-login path is not permitted for products built on the Agent SDK, CI can't reuse
  an interactive login, and the API key gives commercial data terms (no training, ~30-day retention) versus consumer
  terms on the subscription path (training on by default, longer retention). See §10 for the full picture.

## Detailed Findings

### 1. `query()` is async-iterator based (same shape as TS, async/await idiom)

Verified signature from the SDK source
([query.py:11-16](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/query.py)):

```python
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None,
    transport: Transport | None = None,
) -> AsyncIterator[Message]:
```

So the TS `for await (const message of result)` becomes Python `async for message in query(...)`, wrapped in an
`async def main()` that you run with `asyncio.run(main())`. The lesson's top-level `await` (it uses ESM top-level await)
maps to this `asyncio.run` entry point.

### 2. Structured output: `output_format` + `structured_output` (full parity, verified)

The `ClaudeAgentOptions` dataclass has an `output_format` field
([types.py:1889-1895](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/types.py)):

```python
output_format: dict[str, Any] | None = None
"""Output format configuration for structured responses.
When specified, the agent returns structured data matching the schema.
Matches the Messages API structure, e.g.
{"type": "json_schema", "schema": {"type": "object", "properties": {...}}}."""
```

The result lands in `ResultMessage.structured_output`. This is confirmed by the SDK's own e2e test
([test_structured_output.py:24-61](https://github.com/anthropics/claude-agent-sdk-python/blob/main/e2e-tests/test_structured_output.py)):

```python
schema = {
    "type": "object",
    "properties": {
        "file_count": {"type": "number"},
        "has_tests": {"type": "boolean"},
        "test_file_count": {"type": "number"},
    },
    "required": ["file_count", "has_tests"],
}
options = ClaudeAgentOptions(output_format={"type": "json_schema", "schema": schema}, cwd=".")

result_message = None
async for message in query(prompt="...", options=options):
    if isinstance(message, ResultMessage):
        result_message = message

assert result_message.structured_output is not None
```

This is the single most important finding: **the Python SDK does the same native schema-validated structured output as
the TS lesson** — there is no need to fall back to "ask for JSON in the prompt and parse it yourself."

### 3. zod → Pydantic (the only conceptual translation)

zod has no Python twin, but the lesson only uses zod for two things, both of which Pydantic covers:

1. **Single source of truth for the schema** → a Pydantic `BaseModel` whose `model_json_schema()` produces the dict you
   hand to `output_format`.
2. **Runtime validation of the model's output** → `Review.model_validate(result.structured_output)` replaces zod's
   `REVIEW_SCHEMA.safeParse(...)`, and it also gives you the typed object back.

The lesson's `.describe()` field-descriptions lever (the "crucial lever" it stresses) maps to Pydantic's
`Field(description=...)`. The descriptions are what carry the 1-10 rubric, because — same as the lesson notes for
Anthropic — **numeric `minimum`/`maximum` bounds are rejected by structured output**, so the range lives in the
description and prompt, not the schema.

Two Pydantic-specific caveats to resolve at implement time (flagged in Open Questions):

- `model_json_schema()` emits **draft 2020-12** with `title` keys and, for nested types, `$defs`/`$ref`. The lesson
  deliberately targeted **draft-07** for the TS SDK. Our schema is flat (no nesting), so there are no `$ref`s; the main
  thing to verify is that the SDK/Messages API accepts the dict as-is.
- Anthropic structured output generally wants `additionalProperties: false` and all properties listed in `required`.
  Pydantic does **not** add `additionalProperties: false` by default — set `model_config = ConfigDict(extra="forbid")`
  to emit it, and make every field required (no defaults).

Because of these caveats, the **lowest-risk path is the hand-written dict schema** (matches the SDK e2e test verbatim),
with Pydantic used purely to _validate and type_ `structured_output` after the fact. Using Pydantic to also _generate_
the schema is the nicer "single source of truth" but needs the two config tweaks above. Both are viable; pick during
planning.

### 4. Tooling: how to reproduce the lesson's `tools: []`

The lesson sets `tools: []` to keep the diff review "narrow and predictable" — no file/bash access, no `CLAUDE.md`
pulled in (it uses a _custom_ `systemPrompt`, not the `claude_code` preset). Python equivalents:

- **Custom system prompt** (not the preset): pass `system_prompt="<reviewer role>"` as a string. This already avoids the
  `claude_code` preset, so project memory/skills are not injected.
- **Don't load repo settings:** `setting_sources=[]` disables loading `.claude/` and `CLAUDE.md` (default is to load all
  of `user`/`project`/`local`). This is the Python knob the lesson's "deliberately cutting off project memory"
  describes.
- **No tools:** `allowed_tools=[]`. Note the Python API exposes `allowed_tools` / `disallowed_tools` rather than a
  single `tools` field. With the diff passed inline in the prompt and a tight `max_turns`, the model has no reason to
  call tools; if you want a hard guarantee, also list the built-ins in `disallowed_tools` (bare names like `"Bash"`,
  `"Read"`, `"Edit"`, `"Write"` remove them from context entirely).

Optional variant (matches the lesson's "let it look into neighbouring files" alternative): allow read-only tools
`allowed_tools=["Read", "Glob", "Grep"]`. Out of scope for the minimal port but worth keeping in mind.

### 5. Turn limit and the two-turn rationale carry over

`max_turns=2` is the direct equivalent of `maxTurns: 2`. The lesson's reasoning holds in Python: turn 1 the model reads
the diff and forms the assessment, turn 2 it emits the structured JSON. Be aware of a Python result subtype
`error_max_structured_output_retries` — if the model struggles to satisfy the schema, the SDK may need a little
headroom; if you see that subtype, bump `max_turns` slightly rather than fighting it.

### 6. Cost & usage: read straight off `ResultMessage` (parity, verified)

`ResultMessage` (from
[types.py](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/types.py)):

```python
@dataclass
class ResultMessage:
    subtype: str  # "success", "error_during_execution", "error_max_turns",
                  # "error_max_budget_usd", "error_max_structured_output_retries"
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    stop_reason: str | None = None
    total_cost_usd: float | None = None          # ready cost in USD — no rate table needed
    usage: dict[str, Any] | None = None          # input_tokens, output_tokens, cache_* (snake_case)
    result: str | None = None
    structured_output: Any = None                # parsed JSON-schema output
    model_usage: dict[str, Any] | None = None    # per-model: inputTokens, outputTokens, costUSD ...
    permission_denials: list[Any] | None = None
    errors: list[str] | None = None
    api_error_status: int | None = None
    uuid: str | None = None
```

So the lesson's cost section maps 1:1:

- `message.usage.input_tokens` → `result.usage["input_tokens"]`
- `message.total_cost_usd` → `result.total_cost_usd`
- `message.modelUsage` → `result.model_usage` (per-model `inputTokens`/`outputTokens`/`costUSD`, camelCase keys inside
  the dict, just like TS)
- `num_turns`, `duration_ms` are present too.

The lesson's note that on the _assemble-your-own_ side you only get tokens and must multiply by rates does **not** apply
here — the ready-made agent gives `total_cost_usd` for free.

Per-turn telemetry (the lesson's `onStepFinish`): the Python `query()` already yields intermediate `AssistantMessage`s
with a `.usage` dict during the loop, so you can log incremental usage by inspecting messages as they stream, rather
than a dedicated callback.

### 7. Hard budget cap: `max_budget_usd` (parity)

The lesson's `maxBudgetUsd: 0.5` (Claude Agent SDK's built-in hard ceiling) is `max_budget_usd=0.5` in
`ClaudeAgentOptions`. When exceeded the run stops and `ResultMessage.subtype` is `"error_max_budget_usd"` — the same
error subtype you branch on for failure handling.

### 8. Error handling: branch on `subtype` / `is_error`

The lesson reads `message.subtype !== "success"` then `message.errors`. Python is identical:

```python
if result.subtype == "success":
    review = Review.model_validate(result.structured_output)
else:
    raise RuntimeError(f"Review failed ({result.subtype}): {'; '.join(result.errors or [])}")
```

`ResultMessage` carries `errors: list[str] | None`, mirroring TS `message.errors`.

### 9. Reading the diff from stdin

The lesson's `readDiff()` (consume `process.stdin`) becomes a one-liner: `sys.stdin.read()`. So the invocation stays
`git diff | uv run python review.py` (or via a console-script entry point).

### 10. Install, deps, and auth for this repo

- **Add the dep:** `uv add claude-agent-sdk` (the repo uses uv; see `CLAUDE.md` / `pyproject.toml`). Requires Python ≥
  3.10 — the repo is on 3.12, fine. Recent versions bundle the Claude Code CLI, so no Node install step; pin the version
  in `pyproject.toml`.
- **Pydantic** is not currently a direct dependency (the repo depends on `openai`, `django`, etc.), so if we go the
  Pydantic route, `uv add pydantic` (it's almost certainly already present transitively via Django/openai, but make it
  explicit).
- **Auth (two paths):**
  - **Local, personal use (our scope):** no key needed. Log in to Claude Code with your Claude Pro/Max subscription and
    leave `ANTHROPIC_API_KEY` unset — the SDK uses your subscription credentials and the run draws from your normal
    subscription limits. (Anthropic announced a separate metered "Agent SDK credit" pool from 2026-06-15, but
    [paused it](https://www.digitalapplied.com/blog/anthropic-claude-credit-overhaul-june-15-2026), so subscription
    usage is unchanged for now.) **This trick is OK only for local, personal CLI use.**
  - **Shared / CI use (later, M5L3):** set `ANTHROPIC_API_KEY` from the [Console](https://platform.claude.com/) — a
    _separate_ product with its own pay-as-you-go billing (a Pro subscription does **not** include Console API credits).
    Required because the subscription-login path is not permitted for products built on the Agent SDK and CI can't reuse
    an interactive login; it also gives commercial data terms (no training, ~30-day retention) versus consumer terms on
    the subscription path. Add `ANTHROPIC_API_KEY` to `.env.example` the same way `OPENROUTER_API_KEY` is documented.
  - Either way, this key is a _different_ provider/key than the app's existing `OPENROUTER_API_KEY` (used for the Django
    text-generation feature) — the review tool is a standalone dev/CI utility, not part of the Django app runtime.

## Proposed runnable Python design (port of `review.ts`)

Conceptual reference implementation (to be refined in `/10x-plan` — descriptions/rubric trimmed for brevity, matching
how the lesson presents its snippets):

```python
import asyncio
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

SYSTEM_PROMPT = (
    "You are a precise, constructive code reviewer evaluating a pull request. "
    "Assess the given diff against five criteria on a scale of 1-10 "
    "(implementation correctness, idiomaticity, complexity, test coverage relative to risk, "
    "security). Then issue a binding verdict (pass/fail) and a short Markdown summary."
)

class Review(BaseModel):
    # extra='forbid' -> emits additionalProperties:false for Anthropic structured output
    model_config = ConfigDict(extra="forbid")

    implementation_correctness: int = Field(
        description="Whether the code does what it declares (scale 1-10)."
    )
    idiomaticity: int = Field(description="Conformance with language/project conventions (1-10).")
    complexity: int = Field(description="Simplicity relative to the problem (1-10).")
    test_risk_coverage: int = Field(description="Test coverage proportional to risk (1-10).")
    security_safety: int = Field(description="No vulnerabilities or secret leaks (1-10).")
    verdict: Literal["pass", "fail"] = Field(description="Binding verdict for the whole change.")
    summary: str = Field(description="Markdown summary, ready as a PR comment.")

async def review(diff: str) -> Review:
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="claude-sonnet-4-6",
        max_turns=2,
        allowed_tools=[],          # no tools, like the lesson's tools: []
        setting_sources=[],        # don't pull in CLAUDE.md / .claude config
        output_format={"type": "json_schema", "schema": Review.model_json_schema()},
        # max_budget_usd=0.5,      # optional hard cap, == maxBudgetUsd
    )

    result_message: ResultMessage | None = None
    async for message in query(prompt=f"Review this diff:\n\n{diff}", options=options):
        if isinstance(message, ResultMessage):
            result_message = message

    if result_message is None:
        raise RuntimeError("The agent returned no result")
    if result_message.subtype != "success":
        raise RuntimeError(
            f"Review failed ({result_message.subtype}): "
            f"{'; '.join(result_message.errors or [])}"
        )
    # cost/usage available here: result_message.total_cost_usd, result_message.usage, .model_usage
    return Review.model_validate(result_message.structured_output)

def main() -> None:
    diff = sys.stdin.read()
    print(review_to_json(asyncio.run(review(diff))))  # serialise + optionally print usage/cost
```

If the `model_json_schema()` dict turns out not to be accepted cleanly (draft / `title` keys), the fallback is a
hand-written dict schema identical in shape to the SDK e2e test, keeping `Review` only for post-hoc validation.

## Code References

- `your-first-team-agent-sdk-costs-metrics.md:188-229` — the TS `review.ts` being ported
- `your-first-team-agent-sdk-costs-metrics.md:101-155` — the shared zod schema + `.describe()` lever
- `your-first-team-agent-sdk-costs-metrics.md:623-687` — cost/usage/`maxBudgetUsd` section
- `pyproject.toml:1-30` — current deps (uv, Python 3.12; no `claude-agent-sdk`/`pydantic` yet)
- `CLAUDE.md` — uv conventions, `.env` loading, type-hints + ruff + mypy expectations
- `context/changes/agentic-review/change.md` — the change identity (CLI review tool via Claude Code SDK)

## External References (current docs, fetched 2026-06-19)

- Python SDK reference: https://code.claude.com/docs/en/agent-sdk/python — `query()`, `ClaudeAgentOptions`
  (`system_prompt`, `model`, `max_turns`, `allowed_tools`, `disallowed_tools`, `setting_sources`, `output_format`,
  `max_budget_usd`), `ResultMessage`.
- Agent SDK overview / install / auth: https://code.claude.com/docs/en/agent-sdk/overview
  (`pip install claude-agent-sdk`, `ANTHROPIC_API_KEY`, claude.ai login not permitted for SDK products).
- SDK source (verified): `src/claude_agent_sdk/types.py` (`output_format`, `ResultMessage`),
  `e2e-tests/test_structured_output.py` (working structured-output example).

## Architecture Insights

- **Category match:** the lesson frames the core choice as "ready-made agent vs assemble-your-own." Picking the Claude
  Agent SDK keeps us firmly in the _ready-made_ category, which is why we get `total_cost_usd`, `max_budget_usd`, native
  structured output, and the hidden tool loop for free — the trade-off (Anthropic-only models, tied runtime) is
  acceptable for an internal review tool.
- **Pydantic is the repo-idiomatic schema choice** and aligns with the project's "type hints on all new code" + mypy
  convention from `CLAUDE.md`. It plays the exact role zod plays in the lesson.
- **Standalone utility, not app runtime:** this tool is a dev/CI script. It should not import Django or live inside the
  request path; keep it self-contained (its own module + console entry) so the `ANTHROPIC_API_KEY` dependency never
  affects the app booting (mirrors how the app already boots without `OPENROUTER_API_KEY`).
- **Determinism levers** the lesson stresses (custom system prompt, no preset, no tools, tight turns) all have clean
  Python knobs (`system_prompt` string, `setting_sources=[]`, `allowed_tools=[]`, `max_turns=2`) — nothing about the
  predictability story is lost in translation.

## Historical Context (from prior changes)

- `context/changes/agentic-review/change.md` — opened 2026-06-19; goal is an automatic agentic CLI review tool for this
  repo using the Claude Code SDK. This research advances it to `preparing`.
- `context/foundation/lessons.md` — two standing rules apply at implement time: **verify Docker build before committing
  dep changes** (adding `claude-agent-sdk` touches deps), and **sync GitHub issues** with context changes.

## Related Research

- None yet under `context/changes/**/research.md`. This is the first research artifact for `agentic-review`.

## Open Questions

1. **Pydantic schema acceptance:** confirm at implement time that `Review.model_json_schema()` (draft 2020-12, with
   `title` keys, `extra="forbid"` → `additionalProperties:false`) is accepted by `output_format` as-is. If not, use a
   hand-written dict schema and keep Pydantic only for validation.
2. **Auth posture:** _Resolved for our scope._ Use the subscription-login trick (no key) for local, personal CLI use —
   the lesson's approach, confirmed valid since the 2026-06-15 separate-credit change was paused. Revisit only when
   sharing the tool or wiring CI (M5L3): there a Console `ANTHROPIC_API_KEY` is required. See §10.
3. **CLI version pinning:** confirm the installed `claude-agent-sdk` version bundles the CLI on the target machines; pin
   it in `pyproject.toml`.
4. **Tool hard-lock:** decide whether `allowed_tools=[]` + `setting_sources=[]` is sufficient, or whether to also
   enumerate built-ins in `disallowed_tools` for a guaranteed no-tool run.
5. **Output serialisation/exit code:** define how the CLI prints the result (pretty JSON like the lesson) and whether
   `verdict == "fail"` should set a non-zero exit code (useful for later CI).
