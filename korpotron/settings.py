"""
Django settings for korpotron project.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

try:
    import django_stubs_ext

    django_stubs_ext.monkeypatch()
except ImportError:
    pass

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ["SECRET_KEY"]

DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

# FLY_APP_NAME is injected automatically by Fly.io at runtime — no secret needed.
# ALLOWED_HOSTS env var adds extra hosts (local dev, custom domains).
_fly_app = os.environ.get("FLY_APP_NAME")
_extra_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS: list[str] = ([f"{_fly_app}.fly.dev"] if _fly_app else []) + [
    h.strip() for h in _extra_hosts.split(",") if h.strip()
]

CSRF_TRUSTED_ORIGINS: list[str] = [f"https://{_fly_app}.fly.dev"] if _fly_app else []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
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
        "DIRS": [BASE_DIR / "templates"],
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

# SQLite doesn't support select_for_update() row-level locking (Django 6.x dropped
# support). IMMEDIATE mode acquires the write lock at transaction start, giving the
# same serialisation guarantee needed by the rate-limit check.
# File-based test DB avoids in-memory shared-cache mode (which raises SQLITE_LOCKED
# instead of SQLITE_BUSY, bypassing the busy-handler retry on concurrent BEGIN IMMEDIATE).
if DATABASES["default"].get("ENGINE") == "django.db.backends.sqlite3":
    DATABASES["default"].setdefault("OPTIONS", {})["transaction_mode"] = "IMMEDIATE"
    DATABASES["default"].setdefault("TEST", {}).setdefault(
        "NAME", str(BASE_DIR / "test.sqlite3")
    )

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# OpenRouter (LLM provider) — see ADR 001. The API key is read lazily: it
# defaults to empty so the app boots (and tests run with a patched client)
# without it; the generation call fails loudly only when actually invoked.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/auto:free")
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)

DAILY_GENERATION_LIMIT = int(os.environ.get("DAILY_GENERATION_LIMIT", "100"))
