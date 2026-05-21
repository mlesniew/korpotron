# CLAUDE.md

## Critical

Note taht `SECRET_KEY` in `korpotron/settings.py` is the insecure Django scaffold default.  This needs updated before any production deployment.

## Stack

Django 6.0.5 · Python 3.12 · uv · SQLite (dev) · Fly.io (prod) · GitHub Actions CI

## Setup

```
uv run manage.py migrate
uv run manage.py runserver
```

Use **uv** to add packages — not pip. Example: `uv add django-environ`

## Commands

| Task | Command |
|------|---------|
| Run dev server | `python manage.py runserver` |
| Make migrations | `python manage.py makemigrations` |
| Apply migrations | `python manage.py migrate` |
| Run tests | `pytest` |
| Lint | `ruff check .` |
| Format | `ruff format .` |

## Code conventions

- Add **type hints to all new code**. Django doesn't enforce this by default; we compensate with `mypy` (to be wired into CI).
- Lint and format with **ruff** before committing.

## Testing

Tests use **pytest + pytest-django**.

## Commit style

* Imperative first line: `Add login view`, `Fix migration conflict`, `Update settings for Fly`

## Deployment

Fly.io with GitHub Actions auto-deploy on merge to `master`. No deploy workflow is wired yet.
