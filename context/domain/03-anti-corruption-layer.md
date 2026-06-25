---
title: "Korpotron — Anti-Corruption Layer for the LLM Provider"
created: 2026-06-25
type: refactor-plan
---

# Korpotron — Anti-Corruption Layer for the LLM Provider

> A refactoring **PLAN**, not an implementation. No production code is modified here. Builds on
> `context/domain/01-domain-distillation.md` (the domain map) and `context/domain/02-invariant-aggregate-refactor.md`,
> re-verifying every `path:line` citation against the working tree. The objective: find the worst external dependency
> leak crossing layer boundaries, wrap it in a domain-owned Anti-Corruption Layer (ACL), and prove that swapping the
> dependency afterwards touches only the adapter.

---

## Step 0 — Context (discovery, re-verified)

**Source documents:** `context/foundation/prd.md` (authoritative, status `implemented`),
`context/foundation/adr/001-llm-provider-openrouter.md` (the provider decision — central to this plan),
`context/domain/01-domain-distillation.md`, `CLAUDE.md` (stack/conventions).

**Stack** (`CLAUDE.md`, `pyproject.toml:6-14`): Django 6.0.5 · Python 3.12 · uv · SQLite (dev) / Fly.io (prod) ·
**OpenRouter via the `openai` SDK** · pytest + pytest-django · ruff · mypy.

**External runtime dependencies** (`pyproject.toml:7-14`): `dj-database-url`, `django`, `gunicorn`, **`openai`**,
`psycopg2-binary`, `python-dotenv`, `whitenoise`. Of these only `openai` is a _business_ dependency — the others are
framework/infra plumbing. `openai` is the one that carries domain meaning (the text-generation flow, the app's reason to
exist per `prd.md`).

**Layers** (where the core flow lives):

| Layer               | Location                                | Role                                              |
| ------------------- | --------------------------------------- | ------------------------------------------------- |
| Persistence / model | `core/models.py`                        | `Template`, `Option`, `OptionGroup`               |
| Domain service      | `core/llm.py`                           | `build_messages`, `parse_result`, `generate`      |
| API / view (wire)   | `core/views.py`                         | `generate_view` — request → `llm.generate` → JSON |
| Dev tooling         | `tools/eval_prompts.py`                 | reuses `build_messages` / client for prompt evals |
| Tests               | `tests/test_llm.py`, `test_generate.py` | unit + view tests of the flow                     |

**Replaceability intent — quoted.** ADR 001 explicitly frames the provider as swappable:

- `context/foundation/adr/001-llm-provider-openrouter.md:44` — _"Model flexibility: swap models (GPT-4o, Claude,
  Mistral, etc.) by changing a config value, **not the code**"_.
- `context/foundation/adr/001-llm-provider-openrouter.md:57-58` — _"OpenRouter is a middleman… **mitigable post-MVP by
  pointing `base_url` directly at a provider**."_

This is the strongest possible signal for an ACL: the design record promises the provider is replaceable, but the code
binds the `openai` SDK directly into four files across three layers. Intent-vs-code divergence (Step 2 axis c) is
present and documented.

---

## Step 1 — Identify the leaking dependencies

There is exactly one external business dependency, and it leaks. Every file that "knows" `openai` today:

| #   | Leak                                                                                            | Location                                                   | Layer        | Kind of leak                                                     |
| --- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------ | ---------------------------------------------------------------- |
| 1   | `from openai import OpenAI`                                                                     | `core/llm.py:17`                                           | service      | concrete SDK construction                                        |
| 2   | `from openai.types.chat import ChatCompletionMessageParam`                                      | `core/llm.py:18`                                           | service      | **library type in domain signature**                             |
| 3   | `_client: OpenAI` singleton + `OpenAI(...)` factory                                             | `core/llm.py:77`, `core/llm.py:80`, `core/llm.py:84-88`    | service      | SDK object lifecycle                                             |
| 4   | `build_messages(...) -> list[ChatCompletionMessageParam]`                                       | `core/llm.py:96`                                           | service      | **wire type as the domain return type**                          |
| 5   | `client.chat.completions.create(...).choices[0].message.content`                                | `core/llm.py:162-166`                                      | service      | SDK call/response shape                                          |
| 6   | `from openai import OpenAIError` + `except OpenAIError:`                                        | `core/views.py:30`, `core/views.py:267`                    | **API/view** | **SDK error type in the wire layer**                             |
| 7   | `from openai.types.chat import ChatCompletionMessageParam`                                      | `tools/eval_prompts.py:47`                                 | tooling      | wire type re-imported                                            |
| 8   | `client = llm._get_client()` + `client.chat.completions.create(...).choices[0].message.content` | `tools/eval_prompts.py:196-202`                            | tooling      | **duplicated SDK call shape** + reach into private `_get_client` |
| 9   | `from openai import APITimeoutError, OpenAIError`                                               | `tests/test_generate.py:14`                                | test         | SDK error types in tests                                         |
| 10  | `OpenAIError("boom")` as the failure-injection seam                                             | `tests/test_generate.py:223`, `tests/test_generate.py:348` | test         | tests coupled to SDK exceptions                                  |
| 11  | `fake_client.chat.completions.create.return_value = …; .choices[0].message`                     | `tests/test_llm.py:188-199`                                | test         | mock mirrors the SDK shape                                       |

**Count:** the dependency is known by **5 files** spanning **service, view, tooling, and test** layers.

---

## Step 2 — Classify and choose #1

There is only one external business dependency, so "choose the worst leak" reduces to confirming that the `openai` leak
is genuinely severe rather than incidental. Assessed on the three axes:

**(a) Breadth — layers/files affected: SEVERE.** Five files, four layers. The SDK is not confined to a service: its
_types_ (`ChatCompletionMessageParam`) appear in a domain function signature (`core/llm.py:96`), its _exceptions_
(`OpenAIError`) appear in the view layer (`core/views.py:267`), and its _call shape_ is hand-reconstructed in three
independent places (`core/llm.py:162-166`, `tools/eval_prompts.py:197-202`, `tests/test_llm.py:188-199`).

**(b) Replacement risk/cost today: HIGH and diffuse.** To honor ADR 001's "point `base_url` at a provider" — or to move
to a non-OpenAI-shaped SDK (e.g. Anthropic's native client) — you would today edit the service, the view's `except`
clause, the eval tool, and two test files, with no single seam guaranteeing you found them all. The view layer silently
depends on the provider raising an `openai`-shaped exception; a provider swap that raised a different base class would
make `core/views.py:267` stop catching errors, returning 500s instead of the intended 502 — a failure mode invisible to
a grep of the service alone.

**(c) Intent-vs-code divergence: PRESENT and documented.** ADR 001:44 and :57-58 (quoted in Step 0) promise provider
replaceability. The code does not honor it. This is the decisive axis.

**Chosen leak #1: the `openai` SDK.** It is the only external business dependency, it crosses three+ layers, its removal
is currently diffuse and risky, and an accepted ADR explicitly declares it should be swappable. It wins on all three
axes.

---

## Step 3 — Diagnosis (the duplication and the dangerous boundary crossings)

### 3.1 Wire types in domain signatures

`build_messages` — a pure domain function that assembles the prompt — declares its return type as an `openai` wire type:

```python
# core/llm.py:18, 92-96
from openai.types.chat import ChatCompletionMessageParam
...
def build_messages(
    template: Template,
    selected_options: Sequence[Option],
    text: str,
) -> list[ChatCompletionMessageParam]:        # core/llm.py:96
```

The body actually only ever produces plain `{"role": ..., "content": ...}` dicts (`core/llm.py:119-122`) — the SDK type
buys nothing here except coupling. The domain's _output contract_ is expressed in the vendor's vocabulary.

### 3.2 SDK error type in the API/view layer (the dangerous one)

```python
# core/views.py:30, 265-273
from openai import OpenAIError
...
try:
    result = llm.generate(template, options, text)
except OpenAIError:                                   # core/views.py:267
    logger.exception("LLM generation failed")
    return JsonResponse({"error": "Text generation failed. Please try again."}, status=502)
```

The view — the HTTP boundary — imports the LLM vendor SDK purely to name an exception. The mapping "provider failure →
HTTP 502" is a domain/application decision, but it is expressed in `openai`'s type. Swap the provider and this `except`
silently stops matching.

### 3.3 The SDK call shape, reconstructed three times

The exact incantation `client.chat.completions.create(model=…, messages=…).choices[0].message.content or ""` appears in
three independent places, each of which must change together if the provider's response shape changes:

```python
# core/llm.py:162-166  (service — the real call)
completion = client.chat.completions.create(model=settings.OPENROUTER_MODEL, messages=messages)
raw = completion.choices[0].message.content or ""
```

```python
# tools/eval_prompts.py:196-202  (tooling — a SECOND real call, reaching into a private member)
client = llm._get_client()
completion = client.chat.completions.create(model=model, messages=messages, temperature=0)
raw = completion.choices[0].message.content or ""
```

```python
# tests/test_llm.py:188-199  (test — the shape mirrored in a mock)
fake_message.content = "<body>Rewritten.</body>"
fake_completion.choices = [MagicMock(message=fake_message)]
fake_client.chat.completions.create.return_value = fake_completion
```

`tools/eval_prompts.py:196` reaching into `llm._get_client()` (a `_`-prefixed private) is the clearest symptom: the tool
needs the provider, there is no public seam to get it, so it grabs the private one and re-implements the call.

### 3.4 Code does not honor the declared replaceability

ADR 001:44 promises swapping providers is _"not the code"_ — yet the diagnosis above lists production code in the
service **and** the view that names `openai` directly, plus a tool and two test files. The promise is not kept.

---

## Step 4 — Design the ACL

Three pieces: **domain value types** (the only vocabulary the rest of the app speaks), a **narrow port** (domain
interface), and an **adapter** (the single file that imports `openai`). New files follow the existing flat-ish `core/`
layout; the adapter gets its own `core/adapters/` package so the isolation grep (Step 6) is trivial.

### 4.1 Domain value objects — the shape the app owns

`GenerateResult` already exists and is correct (`core/llm.py:71-74`) — a frozen domain VO with `title`/`body`. Keep it.
Add two more so no vendor type crosses a boundary:

```python
# core/llm.py  (domain — no openai import)

@dataclass(frozen=True)
class LlmMessage:
    """One chat message in the app's own vocabulary. Replaces ChatCompletionMessageParam."""
    role: str          # "system" | "user"
    content: str


class LlmError(Exception):
    """Provider-agnostic failure of a generation call. Replaces OpenAIError at every boundary."""


class LlmTimeout(LlmError):
    """The provider did not respond within REQUEST_TIMEOUT. Replaces APITimeoutError."""
```

`build_messages` now speaks the domain type:

```python
def build_messages(
    template: Template,
    selected_options: Sequence[Option],
    text: str,
) -> list[LlmMessage]:
    ...
    return [LlmMessage(role="system", content=system),
            LlmMessage(role="user", content=user)]
```

### 4.2 The narrow port — a domain interface

One method, no vendor leakage in or out. Input: domain `LlmMessage`s + the configured model id. Output: the raw string
the model produced. Failure: `LlmError`/`LlmTimeout`. Parsing stays in the domain (`parse_result`), so the port returns
the raw string, not `GenerateResult` — keeping the adapter dumb.

```python
# core/llm.py  (domain — the contract the rest of the code knows)
from typing import Protocol

class ChatModel(Protocol):
    def complete(
        self,
        messages: Sequence[LlmMessage],
        *,
        model: str,
        temperature: float | None = None,
    ) -> str:
        """Return the raw assistant text. Raise LlmError / LlmTimeout on provider failure."""
        ...
```

### 4.3 The adapter — the ONLY file that imports `openai`

```python
# core/adapters/openrouter.py  (the entire ACL boundary)
from openai import OpenAI, OpenAIError, APITimeoutError
from openai.types.chat import ChatCompletionMessageParam
from django.conf import settings
from core.llm import ChatModel, LlmMessage, LlmError, LlmTimeout

REQUEST_TIMEOUT = 60.0   # moved here from core/llm.py:65 — it is a provider concern

class OpenRouterChatModel:                       # structurally satisfies ChatModel
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=REQUEST_TIMEOUT,
        )

    def complete(self, messages, *, model, temperature=None) -> str:
        wire: list[ChatCompletionMessageParam] = [
            {"role": m.role, "content": m.content} for m in messages   # the ONLY map domain→vendor
        ]
        kwargs = {"model": model, "messages": wire}
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            completion = self._client.chat.completions.create(**kwargs)
        except APITimeoutError as exc:
            raise LlmTimeout(str(exc)) from exc
        except OpenAIError as exc:
            raise LlmError(str(exc)) from exc
        return completion.choices[0].message.content or ""   # the ONLY map vendor→domain
```

### 4.4 Re-wiring the service (keeps the existing test seam)

`generate` keeps its signature and its module-level lazy singleton — only now the singleton is a `ChatModel`, and the
patch target `_get_client` becomes `_get_model` (or is kept as a thin alias to minimise test churn):

```python
# core/llm.py
_model: ChatModel | None = None

def _get_model() -> ChatModel:
    """Return the configured ChatModel singleton. Patch target for tests."""
    global _model
    if _model is None:
        from core.adapters.openrouter import OpenRouterChatModel   # lazy: domain has no openai import
        _model = OpenRouterChatModel()
    return _model

def generate(template, selected_options, text) -> GenerateResult:
    messages = build_messages(template, list(selected_options), text)
    raw = _get_model().complete(messages, model=settings.OPENROUTER_MODEL)
    return parse_result(raw)
```

The lazy import inside `_get_model` is what keeps `core/llm.py` free of any top-level `openai` import while still
defaulting to the real adapter — the domain module compiles and is importable with `openai` uninstalled.

---

## Step 5 — Proof of isolation + before/after

### 5.1 Swapping the library touches only the adapter

To repoint at a direct provider `base_url`, or replace `openai` with another SDK, you edit **only**
`core/adapters/openrouter.py`: change the constructor, the domain→wire map, and the vendor→domain map. Specifically, the
swap does **not** touch:

- **Tables / models** — `core/models.py` never knew `openai`; unaffected.
- **API / wire** — `core/views.py` catches `LlmError` (a domain type); a new adapter just raises the same `LlmError`.
- **UI** — templates receive `{"title", "body"}` JSON built from `GenerateResult` (`core/views.py:282`); the view
  already returns ready domain data, never an `openai` object. No change.
- **Prompt logic** — `build_messages` / `parse_result` are pure domain; unaffected.

### 5.2 Before / after for each duplicated place

| Place                               | Before (knows `openai`)                                                   | After                                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `core/llm.py:18,96`                 | `build_messages -> list[ChatCompletionMessageParam]`                      | `-> list[LlmMessage]` (domain VO)                                                     |
| `core/llm.py:162-166`               | `client.chat.completions.create(...).choices[0].message.content`          | `_get_model().complete(messages, model=…)`                                            |
| `core/llm.py:77-88`                 | `OpenAI` singleton + factory                                              | `ChatModel` singleton; SDK construction moved to adapter                              |
| `core/views.py:30,267`              | `from openai import OpenAIError` / `except OpenAIError:`                  | `from core.llm import LlmError` / `except LlmError:`                                  |
| `tools/eval_prompts.py:47,196-202`  | imports wire type, calls `llm._get_client().chat.completions.create(...)` | `llm._get_model().complete(messages, model=model, temperature=0)`; no `openai` import |
| `tests/test_generate.py:14,223,348` | `OpenAIError("boom")` injection                                           | `LlmError("boom")` injection                                                          |
| `tests/test_llm.py:188-199`         | mock mirrors `.choices[0].message` SDK shape                              | patch `_get_model` with a stub `ChatModel` whose `complete` returns a string          |

The UI layer already receives ready domain data, not a raw library object (`core/views.py:282` serialises `result.title`
/ `result.body`); this is preserved, and the chain that produces them is now vendor-free end to end.

### 5.3 Open questions resolved against the SDK contract — encoded in the ACL

- **What counts as a "provider failure"?** `core/views.py:268-269` already documents that `APIStatusError` subclasses
  may carry the raw provider body in `str(e)`. Both `APITimeoutError` and `APIStatusError` derive from
  `openai.OpenAIError`, so catching `OpenAIError` in the adapter (§4.3) covers them; the timeout is additionally
  promoted to `LlmTimeout`. **Decision encoded in the adapter, not the view.**
- **Where does the request timeout live?** It is a provider concern, not a domain rule — moved from `core/llm.py:65`
  into `core/adapters/openrouter.py` (§4.3). The domain no longer mentions seconds.
- **Does the eval tool need a separate client?** No. It needed `temperature=0` (`tools/eval_prompts.py:200`); the port
  exposes `temperature` as an optional kwarg, so the tool drops its private-member reach-in entirely.

---

## Step 6 — Verification and plan

### 6.1 Success criterion (the grep)

```
grep -rn --include='*.py' -E 'openai|OpenAI|ChatCompletion' . | grep -v '.venv'
```

**Today** this matches 5 files: `core/llm.py`, `core/views.py`, `tools/eval_prompts.py`, `tests/test_generate.py`,
`tests/test_llm.py`.

**After the refactor** it must match **only** files under `core/adapters/` — i.e. `core/adapters/openrouter.py` plus its
dedicated test `tests/test_openrouter_adapter.py`. Every other file speaks `LlmMessage` / `GenerateResult` / `LlmError`.
This grep is the gate for the final phase.

| File                                  | Knows `openai` today |            After            |
| ------------------------------------- | :------------------: | :-------------------------: |
| `core/adapters/openrouter.py`         |       — (new)        | ✅ yes (the ACL — intended) |
| `core/llm.py`                         |          ✅          |             ❌              |
| `core/views.py`                       |          ✅          |             ❌              |
| `tools/eval_prompts.py`               |          ✅          |             ❌              |
| `tests/test_generate.py`              |          ✅          |             ❌              |
| `tests/test_llm.py`                   |          ✅          |             ❌              |
| `core/models.py`, templates, settings |          ❌          |             ❌              |

### 6.2 Phase plan (Conventional Commits; type hints + ruff + pytest per `CLAUDE.md`)

1. **`feat(llm): introduce domain types + ChatModel port`** — add `LlmMessage`, `LlmError`, `LlmTimeout`, and the
   `ChatModel` Protocol to `core/llm.py`. No behaviour change; nothing consumes them yet. `uv run pytest` green.
2. **`refactor(llm): add OpenRouter adapter, route generate() through the port`** — create
   `core/adapters/openrouter.py`; move client construction + `REQUEST_TIMEOUT` there; switch `build_messages` to
   `list[LlmMessage]` and `generate` to `_get_model().complete(...)`. Keep the lazy import so `core/llm.py` has no
   top-level `openai`.
3. **`test(llm): patch the port instead of the SDK shape`** — update `tests/test_llm.py` to patch `_get_model` with a
   stub `ChatModel`; drop the `.choices[0].message` mock mirroring.
4. **`refactor(views): catch LlmError instead of OpenAIError`** — swap the import and `except` at `core/views.py:30,267`
   to the domain error; update `tests/test_generate.py` injections to `LlmError`. Verify the 502 path still triggers.
5. **`refactor(tools): drive eval_prompts through the port`** — replace `llm._get_client()` + raw `create(...)` with
   `llm._get_model().complete(..., temperature=0)`; drop the `openai` import from `tools/eval_prompts.py`.
6. **`test(adapter): cover the OpenRouter adapter in isolation`** — add `tests/test_openrouter_adapter.py` mocking the
   `openai` client to assert the domain→wire and vendor→domain maps and the `OpenAIError → LlmError` /
   `APITimeoutError → LlmTimeout` translation. This is now the _only_ test that may import `openai`.
7. **`chore(llm): enforce isolation`** — run the Step 6.1 grep; confirm it returns only `core/adapters/`. Optionally add
   it as a CI guard. `uv run ruff check . && uv run pytest` green; update ADR 001 with a pointer noting the
   replaceability promise is now structurally enforced by the ACL.

---

## Summary

The only external business dependency, the **`openai` SDK** used to reach OpenRouter, leaks across three layers and is
known by five files: its wire type `ChatCompletionMessageParam` is the return type of the pure domain function
`build_messages` (`core/llm.py:18,96`), its exception `OpenAIError` is caught in the HTTP view (`core/views.py:30,267`),
and its `client.chat.completions.create(...).choices[0].message.content` call shape is hand-reconstructed three times
(`core/llm.py:162-166`, `tools/eval_prompts.py:196-202`, `tests/test_llm.py:188-199`), with the eval tool even reaching
into the private `llm._get_client()`. This is the worst — and only — leak on all three axes, and decisively so because
ADR 001 explicitly promises the provider is swappable _"by changing a config value, not the code"_ (`adr/001:44,57-58`)
while the code binds the SDK directly. The fix is an Anti-Corruption Layer: app-owned value types (`LlmMessage`, the
existing `GenerateResult`, `LlmError`/`LlmTimeout`) plus a narrow `ChatModel` port whose single `complete()` method
takes domain messages and returns a raw string, implemented by one adapter, `core/adapters/openrouter.py`, that alone
imports `openai` and performs the only domain↔vendor mappings. After the seven-phase refactor a single grep for `openai`
returns only the adapter directory; the models, the JSON wire contract, the templates, and the prompt logic never
change, so honoring ADR 001's "point `base_url` at a provider" — or replacing the SDK entirely — becomes a one-file
edit.
