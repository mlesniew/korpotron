# CI Smoke Test for Docker Build and Container Startup (R7) — Plan Brief

> Full plan: `context/changes/docker-smoke-test/plan.md` Research: `context/changes/docker-smoke-test/research.md`

## What & Why

Add a CI job that proves the production Docker image builds, the container starts, and the app serves HTTP 200 — closing
risk R7. Today CI runs `pytest` and `ruff` but never builds or runs the container, so an image that builds yet fails to
boot or serve HTTP would deploy to production undetected.

## Starting Point

`.github/workflows/ci.yml` has `test`, `lint`, and `deploy` (gated on `needs: [test, lint]`, master push only). The
`Dockerfile` already produces a gunicorn image on port 8080; migrations run in prod via Fly's `release_command`, not in
the image. No CI step exercises the running container.

## Desired End State

Every PR and master push builds the image, starts the container, migrates it, and confirms `GET /` returns HTTP 200
before `deploy` can run. `CI / Docker Smoke` is a required status check, so a PR whose container fails to start cannot
merge, and a broken image cannot deploy.

## Key Decisions Made

| Decision             | Choice                                                | Why (1 sentence)                                                                                 | Source   |
| -------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------ | -------- |
| Health probe target  | `GET /` (anonymous landing page)                      | Cheapest unauthenticated 200; no new endpoint needed.                                            | Research |
| Database handling    | Migrate the running container, then probe             | User chose "migrate then probe"; `docker exec` migrate keeps the real gunicorn `CMD` under test. | Plan     |
| Deploy gating        | `deploy needs: [test, lint, docker-smoke]`            | A container that fails to start must not reach production.                                       | Plan     |
| Enforcement          | Add `CI / Docker Smoke` to required checks            | Makes the gate block merges, mirroring the Phase 1 CI pattern.                                   | Plan     |
| Startup confirmation | Poll `curl` with ~30s timeout + `docker logs` on fail | Measures "starts within timeout" and makes failures diagnosable; avoids flaky fixed sleep.       | Plan     |

## Scope

**In scope:**

- New `docker-smoke` job in `ci.yml` (build → run → exec migrate → poll curl → logs-on-fail → teardown)
- Gate `deploy` on the smoke job
- Add `CI / Docker Smoke` to master required status checks
- Update `test-plan.md` §3/§5/§6 to mark Phase 4 done

**Out of scope:**

- New `/health` endpoint; registry push or deploy-mechanism changes
- Testing build-failure / misconfiguration / multi-arch (test-plan negative space)
- Any change to `Dockerfile`, `fly.toml`, or app code; in-container runtime migrations

## Architecture / Approach

One parallel CI job mirroring `test`/`lint`. Shell sequence on `ubuntu-latest` (Docker + curl built in): `docker build`
→ `docker run -d` with `SECRET_KEY` + `ALLOWED_HOSTS=localhost,127.0.0.1` (both required for a 200) →
`docker exec … manage.py migrate` into the live container (same SQLite file) → poll `curl -fsS http://localhost:8080/`
until 200 or timeout → `docker logs` on failure → `docker rm -f` always. Then `deploy` gates on it and branch protection
enforces it.

## Phases at a Glance

| Phase                                    | What it delivers                                 | Key risk                                                       |
| ---------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------- |
| 1. CI smoke job + deploy gate            | Working `docker-smoke` job; deploy depends on it | Probe flakiness on gunicorn warmup (mitigated by poll+timeout) |
| 2. Enforce as required check + close out | `CI / Docker Smoke` required; test-plan updated  | Context string must exist (one run) before `gh api` can add it |

**Prerequisites:** Phase 2 needs Phase 1's job to have run green once so the check context exists; `gh` authenticated
with repo-admin rights for branch protection. **Estimated effort:** ~1 session, 2 phases.

## Open Risks & Assumptions

- Assumes `GET /` stays DB-light; migrations are applied anyway, so a future DB-touching `/` is covered.
- Assumes `ubuntu-latest` keeps shipping Docker + curl (true today).
- Branch protection is an outward-facing repo-settings change; must read current protection before `PUT` to avoid
  dropping existing `CI / Test` / `CI / Lint` contexts or settings.

## Success Criteria (Summary)

- A PR's `CI / Docker Smoke` check builds, starts, and probes the container green; a broken container fails it with
  visible `docker logs`.
- `deploy` cannot run, and a PR cannot merge, unless the smoke check passes.
- `test-plan.md` records R7 / Phase 4 as covered.
