---
id: 001
title: Use OpenRouter as the LLM Provider
status: Accepted
date: 2026-06-01
---

# ADR 001: Use OpenRouter as the LLM Provider

## Status

Accepted

## Context

S-03 (`text-generation-flow`) requires an external text-generation API. The app assembles a prompt from a stored template plus selected option text, submits it to an LLM, and displays the result verbatim. A provider decision was needed before S-03 could be planned or built.

The user already has an OpenRouter account with API access. No other provider was under active consideration for this MVP.

## Decision

Use **OpenRouter** as the LLM provider, accessed via the `openai` Python SDK with a `base_url` override:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)
```

The model is configured via an env var (e.g., `OPENROUTER_MODEL`), defaulting to a cost-effective choice such as `openai/gpt-4o-mini`. The `OPENROUTER_API_KEY` secret is set on Fly.io alongside other app secrets.

## Consequences

**Positive:**
- Zero onboarding friction: account and API key already exist
- Model flexibility: swap models (GPT-4o, Claude, Mistral, etc.) by changing a config value, not the code
- OpenAI-compatible API: one SDK, widely understood interface, minimal new surface area
- Easy to test: mock `openai_client.chat.completions.create` with `unittest.mock.patch` — no additional test dependencies

**Neutral:**
- Extra proxy hop adds ~50–150 ms latency; acceptable since the 60-second full-flow success criterion is about copy-paste friction, not API latency
- Pay-per-token pricing varies by model; negligible at single-user MVP scale

**Negative:**
- OpenRouter is a middleman: an OpenRouter outage means the app cannot generate text. Acceptable for MVP; mitigable post-MVP by pointing `base_url` directly at a provider.
