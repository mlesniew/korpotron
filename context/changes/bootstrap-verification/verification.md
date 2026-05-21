---
bootstrapped_at: 2026-05-21T09:09:54Z
starter_id: django
starter_name: Django (django-admin startproject)
project_name: korpotron
language_family: python
package_manager: uv
cwd_strategy: native-cwd
bootstrapper_confidence: verified
phase_3_status: ok
audit_command: pip-audit --format json
---

## Hand-off

```yaml
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
```

## Why this stack

A solo knowledge worker building a minimal web app in 2 after-hours weeks, with login required and LLM-based text generation as the core feature. Django is the recommended default for (web-app, python): auth, ORM, admin, and migrations ship out of the box, reducing setup friction to near-zero and leaving the limited timeline for product logic rather than infrastructure wiring. Bootstrapper confidence is verified — scaffolding will be smooth. Auth and AI feature flags are set; payments, realtime, and background jobs are out of scope per PRD non-goals. The one known gap against agent-friendly criteria is that Django does not enforce type hints by default; at small scale this is workable, and the bootstrapper instruction file will note the compensation convention (type hints throughout, mypy in CI). Deployment to Fly.io with GitHub Actions and auto-deploy on merge.

## Pre-scaffold verification

| Signal      | Value                                            | Severity | Notes                                                                 |
| ----------- | ------------------------------------------------ | -------- | --------------------------------------------------------------------- |
| npm package | not run                                          | n/a      | language_family is python; no npm package to check                   |
| GitHub repo | not run                                          | n/a      | docs_url not a GitHub URL; gh CLI unavailable; no recency signal     |

## Scaffold log

**Resolved invocation**: `django-admin startproject korpotron .`
**Strategy**: native-cwd (scaffold directly into the current directory)
**Exit code**: 0
**Pre-flight files-to-touch**: manage.py, korpotron/__init__.py, korpotron/settings.py, korpotron/urls.py, korpotron/wsgi.py, korpotron/asgi.py
**Files written by CLI**: 6
**Pre-existing files preserved**: none

**Note on `{name}` substitution**: The `native-cwd` substitution rule prescribes `{name}=.`, which would produce `django-admin startproject . .` — an invalid invocation (Django requires a Python-identifier package name, not `.`). Bootstrapper used `project_name` (`korpotron`) as `{name}` instead, producing the valid `django-admin startproject korpotron .`. This deviation is intentional and specific to the Django starter's cmd_template shape.

**Pre-step**: Django was not pre-installed. `uv venv` was run to create a virtual environment at `.venv/`, then `uv pip install django` installed Django 6.0.5. These steps are outside `cmd_template` itself but required to make the scaffold command runnable.

## Post-scaffold audit

**Tool**: pip-audit --format json
**Summary**: 0 CRITICAL, 0 HIGH, 0 MODERATE, 0 LOW
**Direct vs transitive**: not distinguished by this tool

Audit: 0 findings across CRITICAL, HIGH, MODERATE, and LOW. Clean tree.

## Hints recorded but not acted on

| Hint                    | Value                  |
| ----------------------- | ---------------------- |
| bootstrapper_confidence | verified               |
| quality_override        | false                  |
| path_taken              | standard               |
| self_check_answers      | null                   |
| team_size               | solo                   |
| deployment_target       | fly                    |
| ci_provider             | github-actions         |
| ci_default_flow         | auto-deploy-on-merge   |
| has_auth                | true                   |
| has_payments            | false                  |
| has_realtime            | false                  |
| has_ai                  | true                   |
| has_background_jobs     | false                  |

## Next steps

Next: a future skill will set up agent context (CLAUDE.md, AGENTS.md). For now, your project is scaffolded and verified — happy hacking.

Useful manual steps in the meantime:
- Review `.venv/` — the virtual environment created during scaffolding. Add it to `.gitignore` if not already present.
- Run `source .venv/bin/activate && python manage.py migrate` to apply the initial Django migrations.
- Run `source .venv/bin/activate && python manage.py runserver` to verify the dev server starts cleanly.
- Address audit findings per your project's risk tolerance — the full breakdown is in this log (currently: none).
