---
date: 2026-06-15T16:17:38+02:00
researcher: Michał Leśniewski
git_commit: 203721da8d79d32470f86dedd558dcae3d30b640
branch: master
repository: mlesniew/korpotron
topic: "CI smoke test for Docker build and container startup (risk R7)"
tags: [research, codebase, docker, ci, github-actions, deployment, R7]
status: complete
last_updated: 2026-06-15
last_updated_by: Michał Leśniewski
---

# Research: CI smoke test for Docker build and container startup (risk R7)

**Date**: 2026-06-15T16:17:38+02:00 **Researcher**: Michał Leśniewski **Git Commit**:
203721da8d79d32470f86dedd558dcae3d30b640 **Branch**: master **Repository**: mlesniew/korpotron

## Research Question

Address risk **R7** (Phase 4 of `context/foundation/test-plan.md`): _"Docker container startup failure undetected in CI
— image builds but container fails to start or serve HTTP."_ What is the cheapest CI step that proves protection: the
image **builds**, the container **starts within a timeout**, and a health URL **responds HTTP 200**? Gather the context
the test plan flags as needed: Dockerfile contents, health-check URL, required env vars at startup, and the CI workflow
integration point.

## Summary

The pieces for a `build → run → curl → teardown` smoke job all exist and are well-defined:

- **Build**: A working multi-stage `Dockerfile` produces a gunicorn-served image exposing port `8080`. `collectstatic`
  runs at build time (stage 2) with placeholder env; migrations do **not** run in the image — production runs them via
  the Fly.io `release_command`.
- **Run**: `CMD` is `gunicorn korpotron.wsgi --bind 0.0.0.0:8080 …`. The only env var that **blocks boot** is
  `SECRET_KEY` (read with no default — `KeyError` if missing). To avoid `400 DisallowedHost`, the smoke run must also
  set `ALLOWED_HOSTS` (e.g. `localhost,127.0.0.1`), because `FLY_APP_NAME` (the prod source of allowed hosts) is absent
  in CI.
- **Curl**: There is **no dedicated health endpoint**. The cheapest unauthenticated 200 is `GET /` (`HomeView`), which
  renders `landing.html` for anonymous users with **no DB access** — so it should return 200 on a fresh, unmigrated
  container (see [Open Questions](#open-questions) — the smoke test itself is the right place to confirm this
  empirically, which is precisely R7's point).
- **Integrate**: Add a parallel `docker-smoke` job to `.github/workflows/ci.yml` (alongside `Test`/`Lint`), gate
  `deploy` on it (`needs: [test, lint, docker-smoke]`), and add `CI / Docker Smoke` to the required status checks on
  `master` — mirroring the Phase 1 `ci-quality-gate` pattern.

The key anti-pattern R7 warns against (treating "build exits 0" as success without verifying the running container
serves HTTP) is exactly what the `curl -f http://localhost:8080/` step prevents.

## Detailed Findings

### Docker image & startup

- **`Dockerfile`** — multi-stage build:
  - Stage 1 `builder`: `uv sync --frozen --no-dev --no-install-project`
    ([Dockerfile#L1-L4](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/Dockerfile#L1-L4))
  - Stage 2 `static-builder`: runs `collectstatic` at **build time** with placeholders
    `SECRET_KEY=placeholder ALLOWED_HOSTS=localhost`
    ([Dockerfile#L6-L16](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/Dockerfile#L6-L16))
  - Stage 3 final: `python:3.12-slim-bookworm`, copies `.venv` + source + `staticfiles/`; sets
    `DJANGO_SETTINGS_MODULE=korpotron.settings`; `EXPOSE 8080`; runs as **root** (no `USER` set)
    ([Dockerfile#L18-L33](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/Dockerfile#L18-L33))
- **Start command** (`CMD`):
  `gunicorn korpotron.wsgi --bind 0.0.0.0:8080 --workers 2 --timeout 30 --access-logfile - --error-logfile -`
  ([Dockerfile#L28-L33](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/Dockerfile#L28-L33))
- **No ENTRYPOINT, no entrypoint script, no migrations at runtime.** Migrations run only in prod via Fly's
  `release_command = "python manage.py migrate"`
  ([fly.toml#L9](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/fly.toml#L9));
  internal port `8080`, `force_https = true`
  ([fly.toml](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/fly.toml)).
- **`.dockerignore`** uses deny-all-then-allow: `*` then
  `!pyproject.toml !uv.lock !manage.py !korpotron/ !templates/ !static/ !core/`
  ([.dockerignore](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/.dockerignore)).
  Note: `tests/` and `.env` are excluded from the build context.
- WSGI app: `korpotron/wsgi.py`
  ([wsgi.py](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/korpotron/wsgi.py)).

### Health URL & routes

- Root URLconf includes `core.urls` at `""`
  ([korpotron/urls.py#L21-L25](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/korpotron/urls.py#L21-L25)).
- **No dedicated health/status endpoint.** `core/urls.py` defines the app routes
  ([core/urls.py](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/core/urls.py)).
- **`GET /` → `HomeView`** returns `landing.html` for anonymous users, `generate.html` for authenticated users — HTTP
  200 either way, no login required
  ([core/views.py#L143-L155](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/core/views.py#L143-L155)).
  The anonymous branch performs no ORM query.
- Every other app URL (`/templates/…`, `/option-groups/…`, `/generate/`) is `LoginRequired`, so an unauthenticated
  request returns **302** to `/accounts/login/`, not 200 — unsuitable as a health probe. `/accounts/login/` does return
  200 but renders a form (heavier, and exercises auth templates). **`GET /` is the cheapest correct probe.**

### Required env vars at startup

From `korpotron/settings.py`
([settings.py](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/korpotron/settings.py)):

| Variable                                   | Boot-blocking?               | How read                                                             | Default                                   |
| ------------------------------------------ | ---------------------------- | -------------------------------------------------------------------- | ----------------------------------------- |
| `SECRET_KEY`                               | **Yes**                      | `os.environ["SECRET_KEY"]` (settings.py#L22)                         | none → `KeyError`                         |
| `ALLOWED_HOSTS`                            | Effectively yes for HTTP 200 | composed from `FLY_APP_NAME` + `ALLOWED_HOSTS` (settings.py#L28-L32) | `[]` → `400 DisallowedHost` in CI         |
| `DEBUG`                                    | No                           | `os.environ.get("DEBUG", "False")` (settings.py#L24)                 | `False`                                   |
| `DATABASE_URL`                             | No                           | `dj_database_url.config(default=sqlite://…)` (settings.py#L76-L93)   | SQLite file `db.sqlite3`                  |
| `OPENROUTER_API_KEY`                       | No                           | (settings.py#L127)                                                   | `""` (generation fails only when invoked) |
| `OPENROUTER_MODEL` / `OPENROUTER_BASE_URL` | No                           | (settings.py#L128-L131)                                              | sensible defaults                         |
| `DAILY_GENERATION_LIMIT`                   | No                           | (settings.py#L133)                                                   | `100`                                     |

- `.env` is loaded via `python-dotenv` `load_dotenv()` (settings.py#L18), but `.env` is **not** in the Docker build
  context (`.dockerignore`), so the container relies entirely on `-e` flags / Fly secrets.
- WhiteNoise middleware serves static files regardless of `DEBUG`; static assets are baked in at build time, so static
  serving does not depend on runtime env.

### CI workflow integration point

`.github/workflows/ci.yml`
([ci.yml](https://github.com/mlesniew/korpotron/blob/203721da8d79d32470f86dedd558dcae3d30b640/.github/workflows/ci.yml)):

- Triggers: `push` to `master` + `pull_request` targeting `master`.
- `test` job (`name: Test`): `actions/checkout@v6` → `astral-sh/setup-uv@v8.2.0` (py 3.12, cache) → `uv run pytest` with
  `SECRET_KEY: ci-placeholder-not-used-in-production`.
- `lint` job (`name: Lint`): same setup → `uv run ruff check .`.
- `deploy` job (`name: Deploy`): `needs: [test, lint]`,
  `if: github.event_name == 'push' && github.ref == 'refs/heads/master'`, `concurrency: fly-deploy`, installs flyctl and
  runs `flyctl deploy --remote-only`.
- The workflow `name: CI` makes check contexts render as `CI / Test`, `CI / Lint`, etc. — the job's `name:` is the
  suffix after `CI / `.

**Where the new job goes:** a parallel `docker-smoke` job (`name: Docker Smoke` → context `CI / Docker Smoke`), running
on every PR and push (no `if:` master guard), then `deploy` updated to `needs: [test, lint, docker-smoke]`.
`ubuntu-latest` ships Docker + buildx + curl by default, so no extra setup action is required.

## Code References

- `Dockerfile:1-33` — multi-stage build; gunicorn `CMD` on `0.0.0.0:8080`; runs as root; no runtime migrations
- `.dockerignore` — deny-all-then-allowlist; excludes `tests/` and `.env`
- `fly.toml:9,12,20-21` — `release_command` migrate, internal port 8080, force HTTPS
- `korpotron/settings.py:22` — `SECRET_KEY = os.environ["SECRET_KEY"]` (only hard boot requirement)
- `korpotron/settings.py:28-32` — `ALLOWED_HOSTS` from `FLY_APP_NAME` + `ALLOWED_HOSTS` env
- `korpotron/settings.py:76-93` — SQLite default DB; IMMEDIATE transaction mode
- `korpotron/urls.py:21-25` — root URLconf includes `core.urls`
- `core/urls.py` — app routes; no health endpoint
- `core/views.py:143-155` — `HomeView`; `GET /` anonymous → `landing.html`, HTTP 200, no DB
- `.github/workflows/ci.yml` — `test` / `lint` / `deploy` jobs; deploy gated on `needs: [test, lint]`

## Architecture Insights

- **Build-time vs runtime split**: static collection happens at build; migrations happen at deploy (Fly
  `release_command`), never in the image. A CI smoke test therefore validates _startup + HTTP serving_, not schema state
  — which matches R7's scope (the negative space explicitly excludes misconfiguration scenarios).
- **`GET /` is intentionally DB-free for anonymous users**, making it a near-ideal health probe without adding a
  dedicated endpoint. This avoids over-engineering (no new view/route needed) and keeps the test honest: it exercises
  gunicorn + WSGI + middleware + template rendering.
- **`SECRET_KEY` is the single fail-fast boot dependency** — consistent with how the existing `Test` job already injects
  a throwaway `SECRET_KEY`. The smoke job should reuse the same placeholder convention.
- **`ALLOWED_HOSTS` is the subtle gotcha**: production derives it from `FLY_APP_NAME`, which is absent in CI, so the
  smoke run must pass `ALLOWED_HOSTS` explicitly or every curl gets a 400. This is a real trap the smoke test must
  encode, not assume.
- **Check-context naming is load-bearing**: branch protection lists exact strings (`CI / Test`, `CI / Lint`). Adding a
  required check means both shipping the job _and_ updating the protection contexts via `gh api` — a two-step landing
  (the second step is post-merge, once the context exists).

## Historical Context (from prior changes)

- **Phase 1 — `context/archive/2026-06-05-ci-quality-gate/`** (risk R1): established the CI patterns this phase should
  mirror — workflow `name: CI`, per-job `name:` → check context, and branch protection via
  `gh api repos/<repo>/branches/master/protection` with `required_status_checks.strict: true` and a `contexts` array
  (`["CI / Test", "CI / Lint"]`), `enforce_admins: false`. Phase 4 adds `"CI / Docker Smoke"` to that array.
- **Phase 3 — `context/changes/rate-limit-testing/`** (risks R4/R5/R6): established the change-doc conventions to follow
  here — `plan.md` Progress section with `- [ ]`/`- [x]` checkboxes, append ` — <commit sha>` when a step lands, do not
  rename step titles (they're searchable anchors).
- **`context/foundation/lessons.md`** — _"Verify Docker build before committing"_ (the prior-art lesson that seeded R7)
  and _"Sync GitHub issues with context changes"_ (update the GitHub issue when this change progresses).

## Related Research

- `context/foundation/test-plan.md` §2 (R7 row + Risk Response Guidance), §3 Phase 4, §5 (coverage gap), §6 Phase 4
  cookbook stub — the source spec for this work.
- `context/archive/2026-06-05-ci-quality-gate/research.md` — prior CI-workflow research (sibling phase).

## Open Questions

1. **Does an unmigrated container return 200 on `GET /`?** Analysis says yes — the anonymous `HomeView` branch issues no
   ORM query, and Django's session/auth middleware only hit the DB when a session cookie is present (a bare `curl` sends
   none). The two sub-agents differed on this in the abstract. **Resolution path**: the smoke test is the correct place
   to settle it empirically. If `curl -f /` ever fails on a fresh container, the fix is to run
   `python manage.py migrate` before the probe (or add it to a container entrypoint) — but the plan should _start_
   without migrations and only add them if the empirical run demands it.
2. **`docker run -d` startup race**: gunicorn needs a moment to bind. The probe should poll with a retry/timeout (e.g. a
   short `until curl -fsS … ; do sleep 1; done` capped at N seconds) rather than a fixed `sleep`, so the test measures
   "starts within timeout" (R7's "what would prove protection") rather than flaking.
3. **Capture container logs on failure**: to make a failed smoke test actionable, the job should `docker logs <id>` on
   failure before teardown — otherwise R7 failures are detected but not diagnosable.
4. **Required-check rename**: confirm the exact rendered context string (`CI / Docker Smoke`) after the first run before
   wiring branch protection, since it must match byte-for-byte.

---

_Next step: `/10x-plan docker-smoke-test` to turn this into an implementation plan._
