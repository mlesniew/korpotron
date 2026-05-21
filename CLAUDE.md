# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

Django 6.0.5 · Python 3.12 · uv · SQLite (dev) · Fly.io (prod) · GitHub Actions CI

## Setup

```
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
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

## Adding a Django app

```
python manage.py startapp <appname>
```

Then register it in `INSTALLED_APPS` in `korpotron/settings.py`.

## Testing

Tests use **pytest + pytest-django**. `pytest.ini` (or `pyproject.toml [tool.pytest]`) must set `DJANGO_SETTINGS_MODULE=korpotron.settings`. Add this before running tests for the first time.

## Security gotcha

`SECRET_KEY` in `korpotron/settings.py` is the insecure Django scaffold default. Move it to an environment variable (`django-environ` or `python-decouple`) before any production deployment.

## Commit style

Imperative single-line: `Add login view`, `Fix migration conflict`, `Update settings for Fly`.

## Deployment

Fly.io with GitHub Actions auto-deploy on merge to `master`. No deploy workflow is wired yet.
