---
starter_id: django
package_manager: uv
project_name: korpotron
hints:
  language_family: python
  team_size: solo
  deployment_target: fly
  ci_provider: github-actions
  ci_default_flow: auto-deploy-on-merge
  bootstrapper_confidence: verified
  path_taken: standard
  quality_override: false
  self_check_answers: null
  has_auth: true
  has_payments: false
  has_realtime: false
  has_ai: true
  has_background_jobs: false
---

## Why this stack

A solo knowledge worker building a minimal web app in 2 after-hours weeks, with login required and LLM-based text generation as the core feature. Django is the recommended default for (web-app, python): auth, ORM, admin, and migrations ship out of the box, reducing setup friction to near-zero and leaving the limited timeline for product logic rather than infrastructure wiring. Bootstrapper confidence is verified — scaffolding will be smooth. Auth and AI feature flags are set; payments, realtime, and background jobs are out of scope per PRD non-goals. The one known gap against agent-friendly criteria is that Django does not enforce type hints by default; at small scale this is workable, and the bootstrapper instruction file will note the compensation convention (type hints throughout, mypy in CI). Deployment to Fly.io with GitHub Actions and auto-deploy on merge.

## LLM provider

OpenRouter — accessed via the `openai` SDK with `base_url="https://openrouter.ai/api/v1"`. Model configured via env var. See `context/foundation/adr/001-llm-provider-openrouter.md`.
