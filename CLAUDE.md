# CLAUDE.md

## Stack

Django 6.0.5 · Python 3.12 · uv · SQLite (dev) · Fly.io (prod) · OpenRouter (LLM) · GitHub Actions CI

## Setup

```
cp .env.example .env   # then set SECRET_KEY to any non-empty string
uv run manage.py migrate
uv run manage.py runserver
```

Use **uv** to add packages — not pip. Example: `uv add django-environ`

### Environment variables

The project reads configuration from a `.env` file in the project root (loaded automatically via `python-dotenv`).
`.env` is gitignored and never committed.

Copy `.env.example` to `.env` to get started. Required variables:

| Variable              | Required for    | Notes                                                 |
| --------------------- | --------------- | ----------------------------------------------------- |
| `SECRET_KEY`          | App to boot     | Any non-empty string locally                          |
| `OPENROUTER_API_KEY`  | Text generation | App boots without it; Generate fails until set        |
| `OPENROUTER_MODEL`    | Text generation | Optional — defaults to `openrouter/auto:free`         |
| `OPENROUTER_BASE_URL` | Text generation | Optional — defaults to `https://openrouter.ai/api/v1` |

In production (Fly.io) all variables are set as Fly secrets, not via `.env`.

## Commands

| Task             | Command                               |
| ---------------- | ------------------------------------- |
| Run dev server   | `uv run manage.py runserver`          |
| Make migrations  | `uv run manage.py makemigrations`     |
| Apply migrations | `uv run manage.py migrate`            |
| Run tests        | `uv run pytest`                       |
| Lint             | `uv run ruff check .`                 |
| Format           | `uv run ruff format .`                |
| Review a diff    | `git diff \| uv run korpo-review`     |
| Eval prompts     | `uv run python tools/eval_prompts.py` |

`korpo-review` is a standalone dev utility (`tools/review.py`) — it uses the Claude Agent SDK and never imports Django.
No `ANTHROPIC_API_KEY` is needed for local personal use (subscription login fallback); see `.env.example` for CI/shared
use.

`tools/eval_prompts.py` diffs a candidate `SYSTEM_PROMPT` against the current one over a synthetic corpus and appends a
gitignored `eval_log.jsonl`. It bootstraps Django and makes **real** OpenRouter calls, so it needs `OPENROUTER_API_KEY`.
Set `OPENROUTER_EVAL_MODEL` (or pass `--model`) to a **concrete** model — `openrouter/auto:free` routes unpredictably
and makes the before/after diff unreliable. Use `--candidate-file <path>` to load a variant, or `--dry-run` to print the
assembled messages without calling the API.

## Code conventions

- Add **type hints to all new code**. Django doesn't enforce this by default; we compensate with `mypy` (to be wired
  into CI).
- Lint and format with **ruff** before committing.

## Testing

Tests use **pytest + pytest-django**. `DJANGO_SETTINGS_MODULE` is configured in `pyproject.toml` so `uv run pytest`
works with no extra setup.

## Commit style

Use **Conventional Commits**: `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`. Include a scope when the change is
bounded to one area:

```
feat(auth): add password reset flow
fix(templates): correct logout form CSRF handling
chore: update dependencies
```

## Deployment

Fly.io with GitHub Actions auto-deploy on merge to `master`. No deploy workflow is wired yet.
