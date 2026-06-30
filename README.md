# Korpotron

A small web app for people who keep a folder of "good prompts" in a text file and are tired of the copy → paste → tweak
→ copy-back ritual every time they want an LLM to polish an email.

Korpotron lets you save your prompts as **templates**, bolt on reusable **option groups** (Tone: Formal / Casual, that
sort of thing), paste your text, hit Generate, and copy the result. That's the whole product. It does one thing and
politely declines to do anything else.

## What it does

- Create, edit, and delete prompt **templates** (a name + a base prompt).
- Group reusable modifiers into **modifier groups** where you pick at most one option per group (so "Formal" and
  "Casual" can't both win).
- Paste text, pick a template and some options, and get a rewritten version back from an LLM (via
  [OpenRouter](https://openrouter.ai/)).
- Copy the result and get on with your life.

## Running it locally

You'll need [uv](https://github.com/astral-sh/uv) and Python 3.12.

```sh
cp .env.example .env          # then set SECRET_KEY to any non-empty string
uv run manage.py migrate
uv run manage.py runserver
```

Open http://127.0.0.1:8000/ and you're in.

To actually generate text you'll need an OpenRouter key. The app boots without it, but Generate will fail until you set:

```sh
# in .env
OPENROUTER_API_KEY=sk-or-...
```

Optional knobs (sensible defaults if you skip them): `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`,
`DAILY_GENERATION_LIMIT`, `REGISTRATION_PASSPHRASE`.

You'll also want a user to log in as:

```sh
uv run manage.py createsuperuser
```

## Handy commands

| Task             | Command                      |
| ---------------- | ---------------------------- |
| Run dev server   | `uv run manage.py runserver` |
| Apply migrations | `uv run manage.py migrate`   |
| Run tests        | `uv run pytest`              |

## Under the hood

Django 6 · Python 3.12 · SQL(ite) · OpenRouter for the LLM calls · Fly.io in production.
