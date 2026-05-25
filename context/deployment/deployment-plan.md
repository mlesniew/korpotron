# Plan: First Fly.io Deployment

## Context

Fresh Django 6.0.5 scaffold with no deployment infrastructure. `settings.py` uses hardcoded scaffold defaults (insecure `SECRET_KEY`, `DEBUG=True`, SQLite). Fly.io + Supabase + GitHub Actions have been chosen (see `context/foundation/infrastructure.md` and `context/foundation/tech-stack.md`). This plan wires all the pieces: production-ready settings, a uv-based Dockerfile, fly.toml, and GitHub Actions CI.

---

## Step 0 — Prerequisites (manual, before any code work)

All of these must be in place before the first deploy can succeed. None can be automated.

### Fly.io

1. **Install flyctl**
   ```
   curl -L https://fly.io/install.sh | sh
   ```
   Verify: `fly version`

2. **Create a Fly.io account and add billing**
   Fly.io has no free tier. A credit card is required. Sign up at fly.io.

3. **Authenticate**
   ```
   fly auth login
   ```

4. **Register the app name**
   ```
   fly apps create korpotron --org personal
   ```
   If `korpotron` is already taken (app names are global), choose a variant (e.g. `korpotron-app`) and update `app =` in fly.toml accordingly.

### Supabase

5. **Create a Supabase project**
   Create a project at supabase.com. Choose the **Frankfurt (eu-central-1)** region for lowest latency from the Amsterdam Fly.io machine.

6. **Obtain the connection string**
   In the Supabase dashboard: Settings → Database → Connection string → URI tab.
   Select **Transaction pooler** mode (port 6543). The URL format is:
   ```
   postgresql://postgres.PROJECTREF:PASSWORD@HOST:6543/postgres?sslmode=require
   ```
   Save this — it goes into `fly secrets set DATABASE_URL=...` later.

### GitHub

7. **Ensure the repository exists on GitHub**
   GitHub Actions requires the repo to be hosted on GitHub. Push the current `master` branch if not already done.

---

## Step 1 — Add production dependencies

```
uv add gunicorn psycopg2-binary dj-database-url whitenoise
```

- `gunicorn` — WSGI server (not currently in pyproject.toml)
- `psycopg2-binary` — PostgreSQL driver for Supabase
- `dj-database-url` — parses `DATABASE_URL` into Django's `DATABASES` dict
- `whitenoise` — serves static files from Gunicorn; no CDN needed at MVP scale

---

## Step 2 — Rewrite `korpotron/settings.py`

Replace the entire file with a production-ready version that reads config from environment variables. Key changes vs the current scaffold:

- `SECRET_KEY` → `os.environ["SECRET_KEY"]` (hard fail if missing, correct for production)
- `DEBUG` → env var, defaults to `False`
- `ALLOWED_HOSTS` → uses `FLY_APP_NAME` (auto-injected by Fly.io, no secret needed) plus optional `ALLOWED_HOSTS` env var for extra hosts (local dev, custom domains)
- `DATABASES` → `dj_database_url.config(default="sqlite:///...")` (SQLite fallback keeps local dev working without a DB)
- `MIDDLEWARE` → insert `whitenoise.middleware.WhiteNoiseMiddleware` after `SecurityMiddleware`
- Add `STATIC_ROOT = BASE_DIR / "staticfiles"`
- Add `STORAGES` with `CompressedManifestStaticFilesStorage` (whitenoise)
- Add `DEFAULT_AUTO_FIELD` (missing from scaffold, suppresses Django warning)

Full replacement content:

```python
"""
Django settings for korpotron project.
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ["SECRET_KEY"]

DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

# FLY_APP_NAME is injected automatically by Fly.io at runtime — no secret needed.
# ALLOWED_HOSTS env var adds extra hosts (local dev, custom domains).
_fly_app = os.environ.get("FLY_APP_NAME")
_extra_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS: list[str] = (
    [f"{_fly_app}.fly.dev"] if _fly_app else []
) + [h.strip() for h in _extra_hosts.split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "korpotron.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "korpotron.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

---

## Step 3 — Create `Dockerfile`

Multi-stage build. Builder stage uses the official uv image for `uv sync`; runtime stage is a clean `python:3.12-slim-bookworm`. `collectstatic` runs at build time using a placeholder `SECRET_KEY` (inline `RUN`-time env var only — not baked as an `ENV` layer).

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN SECRET_KEY=placeholder ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput
EXPOSE 8080
CMD ["gunicorn", "korpotron.wsgi", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

Notes:
- `--no-install-project` skips installing korpotron as a package (it has no entry points)
- 2 workers is intentional for shared-cpu-1x 256 MB — prevents OOM; increase to 512 MB if needed
- `--access-logfile -` routes logs to stdout so `fly logs` captures them

---

## Step 4 — Create `fly.toml`

Manual creation (do NOT use `fly launch` — it generates a pip-based Dockerfile and misses uv). Region: `ams` (Amsterdam, closest to Poland).

```toml
app = "korpotron"
primary_region = "ams"

console_command = "python manage.py shell"

[build]

[deploy]
  release_command = "python manage.py migrate"

[env]
  PORT = "8080"

[[vm]]
  memory = "256mb"
  cpus = 1
  cpu_kind = "shared"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = false
  min_machines_running = 1
  [http_service.concurrency]
    type = "connections"
    hard_limit = 25
    soft_limit = 20
```

Key decisions:
- `auto_stop_machines = false` + `min_machines_running = 1` — prevents cold starts (highest-likelihood production issue per infrastructure.md risk register)
- `release_command` runs migrations before the new version goes live; deploy aborts if migrations fail
- `force_https = true` — TLS termination at Fly edge

---

## Step 5 — Create `.github/workflows/deploy.yml`

```yaml
name: Deploy to Fly.io

on:
  push:
    branches:
      - master

jobs:
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    concurrency:
      group: fly-deploy
      cancel-in-progress: false

    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

`cancel-in-progress: false` prevents a second push from killing an in-flight migration.

---

## Step 6 — Create `.env.example`

```bash
# Copy to .env for local dev. Never commit .env.
SECRET_KEY=change-me-generate-with-python-secrets
DEBUG=True
# ALLOWED_HOSTS is used locally; on Fly.io the app domain comes from FLY_APP_NAME automatically.
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=
DJANGO_SETTINGS_MODULE=korpotron.settings
```

---

## Step 7 — Update `.gitignore`

Append `.env` (not currently present).

---

## Step 8 — First deploy (manual)

Run these after all code changes are committed and pushed:

1. **Set Fly secrets** (one-time, before first deploy):
   ```
   fly secrets set SECRET_KEY="$(python -c "import secrets; print(secrets.token_urlsafe(50))")"
   fly secrets set DATABASE_URL="postgresql://..."   # from Supabase (Step 0.6)
   ```
   Note: `ALLOWED_HOSTS` is **not** needed — `FLY_APP_NAME` is injected automatically by Fly.io.

2. **Deploy**:
   ```
   fly deploy
   ```
   Watch output with `fly logs`. The `release_command` (migrate) runs first; deploy aborts if it fails.

3. **Wire up GitHub Actions** (enables auto-deploy on future pushes):
   ```
   fly tokens create deploy -a korpotron
   ```
   Add the output token as a secret named `FLY_API_TOKEN` in the GitHub repo (Settings → Secrets and variables → Actions).

All subsequent deploys happen automatically on push to `master`.

---

## Verification

1. `SECRET_KEY=test DEBUG=True python manage.py check` — must pass with no errors
2. `SECRET_KEY=test python manage.py collectstatic --noinput` — verify `staticfiles/` is created
3. After deploy: `https://korpotron.fly.dev/admin/` renders login page (confirms static files served via WhiteNoise)
4. `fly logs` shows Gunicorn startup with no errors
