FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Separate stage for collectstatic: needs the full dep set (including dev)
# because settings.py imports dev-only packages (django_stubs_ext). The final
# image only receives the compiled staticfiles/, not the dev venv.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS static-builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
RUN SECRET_KEY=placeholder ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY . .
COPY --from=static-builder /app/staticfiles /app/staticfiles
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=korpotron.settings
EXPOSE 8080
CMD ["gunicorn", "korpotron.wsgi", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
