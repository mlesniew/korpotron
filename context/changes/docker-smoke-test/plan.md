# CI Smoke Test for Docker Build and Container Startup (R7) — Implementation Plan

## Overview

Add a CI job that proves the production Docker image **builds**, the container **starts within a timeout**, and the app
**serves HTTP 200** — closing risk R7 (Phase 4 of `context/foundation/test-plan.md`). Today CI runs `pytest` and `ruff`
but never builds or runs the container, so an image that builds but fails to boot (or fails to serve HTTP) would reach
production undetected. This plan adds a `docker-smoke` job, gates `deploy` on it, and enforces it as a required status
check on `master`.

## Current State Analysis

- `.github/workflows/ci.yml` has three jobs: `test` (`uv run pytest`), `lint` (`uv run ruff check .`), and `deploy`
  (`flyctl deploy --remote-only`, `needs: [test, lint]`, runs only on push to `master`). Workflow `name: CI` makes check
  contexts render as `CI / Test`, `CI / Lint`, `CI / Deploy`.
- The `Dockerfile` is a working multi-stage build: final `CMD` is `gunicorn korpotron.wsgi --bind 0.0.0.0:8080 …`,
  `EXPOSE 8080`. `collectstatic` runs at build time; **migrations never run in the image** — production applies them via
  Fly's `release_command = "python manage.py migrate"` (`fly.toml:9`).
- `SECRET_KEY` is the only hard boot requirement (`korpotron/settings.py:22`, `os.environ["SECRET_KEY"]`).
  `ALLOWED_HOSTS` is composed from `FLY_APP_NAME` + `ALLOWED_HOSTS` env (`settings.py:28-32`); in CI `FLY_APP_NAME` is
  absent, so without an explicit `ALLOWED_HOSTS` every request gets `400 DisallowedHost`.
- `GET /` (`core/views.py:143-155`, `HomeView`) returns 200 for anonymous users via `landing.html` with no ORM query;
  every other route is `login_required` (302). DB defaults to a SQLite file (`settings.py:76-93`).
- Phase 1 (`context/archive/2026-06-05-ci-quality-gate/`) established the pattern this follows: per-job `name:` → check
  context, branch protection via `gh api …/branches/master/protection` with `required_status_checks.strict: true` and a
  `contexts` array, `enforce_admins: false`.

## Desired End State

- A `docker-smoke` job runs on every PR and push to `master`: it builds the image, runs the container with the same
  `CMD` production uses, applies migrations to that running container, polls `GET /` until it returns HTTP 200 (or fails
  after a timeout, dumping `docker logs`), then tears the container down.
- `deploy` does not run unless `docker-smoke` (and `test`, `lint`) passed.
- `CI / Docker Smoke` is a required status check on `master`, so a PR whose container fails to start cannot merge.
- `context/foundation/test-plan.md` reflects Phase 4 as done.

**Verification**: open a PR; `CI / Docker Smoke` appears as a check and passes; deliberately breaking the container's
startup (locally) makes the smoke steps fail; `gh api …/branches/master/protection` lists `CI / Docker Smoke` in
`required_status_checks.contexts`.

### Key Discoveries:

- Probe target: `GET /` is the cheapest 200 (`core/views.py:143-155`) — no new endpoint needed.
- Boot env in CI: `SECRET_KEY` (any non-empty) + `ALLOWED_HOSTS=localhost,127.0.0.1` are both required to get a 200
  (`settings.py:22`, `settings.py:28-32`).
- The real image `CMD` is gunicorn only; migrations are external — so applying them via `docker exec` into the running
  container both honors "migrate then probe" **and** keeps the job testing the unmodified production `CMD`.
- `ubuntu-latest` GitHub runners ship Docker + buildx + curl by default — no setup action needed.
- Required-check enforcement requires the context string to exist first (one workflow run) before `gh api` can add it —
  so branch protection is Phase 2, after Phase 1's job has run.

## What We're NOT Doing

- Not adding a dedicated `/health` or `/healthz` endpoint — `GET /` suffices.
- Not pushing the image to a registry or changing the deploy mechanism (Fly still builds remotely).
- Not testing Docker build _failure_ modes, env misconfiguration, or multi-arch builds (test plan negative space).
- Not changing the `Dockerfile`, `fly.toml`, or any application code.
- Not adding migrations to the container's runtime `CMD`/entrypoint — migration stays external (Fly `release_command`);
  the smoke job migrates only its own ephemeral test container.

## Implementation Approach

Add one parallel job mirroring `test`/`lint` structure. The job runs a self-contained shell sequence: `docker build` →
`docker run -d` (real `CMD`) → `docker exec … migrate` → poll `curl` → teardown, with `docker logs` emitted if the probe
never succeeds. Gating and enforcement reuse the Phase 1 pattern.

## Critical Implementation Details

- **Migrate against the running container, not a separate one.** SQLite lives on the container's ephemeral filesystem,
  so a one-shot `docker run … migrate` would write to a different container's DB. Start the container with its normal
  `CMD`, then `docker exec <name> python manage.py migrate --noinput` so migrations land in the same SQLite file
  gunicorn serves. This honors the "migrate then probe" decision while leaving the production `CMD` under test.
- **Always tear down, even on failure.** Use `docker rm -f` in a way that runs regardless of probe outcome (e.g. an
  `if: always()` teardown step, or trap-style cleanup), and dump `docker logs` before removal when the probe failed —
  otherwise R7 failures are detected but not diagnosable.
- **Poll, don't sleep.** gunicorn needs a moment to bind; a fixed sleep either flakes or wastes time. Loop `curl -fsS`
  until 200 with a hard cap (~30s) so the job measures "starts within timeout."

## Phase 1: CI smoke job + deploy gate

### Overview

Add the `docker-smoke` job to the CI workflow and make `deploy` depend on it.

### Changes Required:

#### 1. New `docker-smoke` job

**File**: `.github/workflows/ci.yml`

**Intent**: Add a job, parallel to `test`/`lint`, that builds the image, runs the container, migrates it, polls `GET /`
for HTTP 200 with a timeout, dumps container logs on failure, and always removes the container. This is the actual R7
protection.

**Contract**:

- Job key `docker-smoke`, `name: Docker Smoke` (→ check context `CI / Docker Smoke`), `runs-on: ubuntu-latest`.
- Triggers inherited from the workflow (`pull_request` + `push` to `master`); **no** `if:` master guard (must run on PRs
  to be a useful required check).
- Steps: `actions/checkout@v6`; build (`docker build -t korpotron-smoke:ci .`); run detached with
  `-p 8080:8080 -e SECRET_KEY=ci-placeholder-not-used-in-production -e ALLOWED_HOSTS=localhost,127.0.0.1` and a fixed
  `--name`; `docker exec <name> python manage.py migrate --noinput`; poll step; teardown step with `if: always()`.
- Poll contract: loop `curl -fsS http://localhost:8080/` until success or ~30s cap; on timeout print
  `docker logs <name>` and exit non-zero. Example (the loop is the one non-obvious bit):

  ```bash
  for i in $(seq 1 30); do
    if curl -fsS http://localhost:8080/ >/dev/null; then echo "up after ${i}s"; exit 0; fi
    sleep 1
  done
  echo "container did not serve HTTP 200 within 30s"; docker logs korpotron-smoke; exit 1
  ```

- Reuse the exact `SECRET_KEY` placeholder string already used by the `test` job for consistency.

#### 2. Gate deploy on the smoke job

**File**: `.github/workflows/ci.yml`

**Intent**: Prevent a container that fails to start from deploying to production.

**Contract**: change the `deploy` job's `needs: [test, lint]` to `needs: [test, lint, docker-smoke]`. Leave its `if:`
push-to-master guard and `concurrency` block unchanged.

### Success Criteria:

#### Automated Verification:

- Image builds locally: `docker build -t korpotron-smoke:ci .`
- Container serves the probe locally, reproducing the job steps:
  `docker run -d -p 8080:8080 -e SECRET_KEY=ci-placeholder-not-used-in-production -e ALLOWED_HOSTS=localhost,127.0.0.1 --name korpotron-smoke korpotron-smoke:ci`,
  then `docker exec korpotron-smoke python manage.py migrate --noinput`, then `curl -fsS http://localhost:8080/` returns
  200; cleanup `docker rm -f korpotron-smoke`
- Workflow file is valid YAML (parses; `gh workflow view` or a yaml parse succeeds)

#### Manual Verification:

- Open a PR; the `CI / Docker Smoke` check appears and passes
- Temporarily breaking startup (e.g. bad `CMD` locally, or unsetting `SECRET_KEY`) makes the smoke steps fail with
  `docker logs` output visible in the job log
- `deploy` does not start on a push to master until `docker-smoke` has passed

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual
confirmation from the human that the PR-level smoke check ran green before proceeding to Phase 2 (branch protection
needs the check context to exist from a real run).

---

## Phase 2: Enforce as required check + close out test plan

### Overview

Make the smoke check mandatory on `master` and record Phase 4 as complete in the test plan.

### Changes Required:

#### 1. Add `CI / Docker Smoke` to required status checks

**File**: GitHub branch protection on `master` (no repo file — `gh api`)

**Intent**: Make a red smoke check block merges, mirroring how Phase 1 made `CI / Test` and `CI / Lint` required.

**Contract**: `PUT repos/<repo>/branches/master/protection` preserving the existing `required_status_checks`
(`strict: true`, `enforce_admins: false`, `required_pull_request_reviews: null`, `restrictions: null`) and adding
`CI / Docker Smoke` to the `contexts` array so it becomes `["CI / Test", "CI / Lint", "CI / Docker Smoke"]`. Read
current protection first to avoid dropping existing settings.

#### 2. Mark Phase 4 done in the test plan

**File**: `context/foundation/test-plan.md`

**Intent**: Reflect that R7 is now covered.

**Contract**: §3 Phase 4 row status `not started` → `done` with change folder `context/changes/docker-smoke-test/`; §5
"Docker build + container startup" row → **Covered** (Phase 4); §6 "Phase 4 — Docker deployment smoke" stub → filled
with the shipped pattern (build → run → exec migrate → poll curl `/` → teardown; required check `CI / Docker Smoke`;
deploy gated via `needs: [test, lint, docker-smoke]`).

### Success Criteria:

#### Automated Verification:

- Protection lists the new context:
  `gh api repos/<repo>/branches/master/protection -q '.required_status_checks.contexts'` includes `CI / Docker Smoke`

#### Manual Verification:

- A PR with a failing container shows the merge button blocked on `CI / Docker Smoke`
- `test-plan.md` §3/§5/§6 read consistently and reference this change folder

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual
confirmation from the human.

---

## Testing Strategy

### Unit Tests:

- None — this change adds no application code. The "test" is the CI job itself exercising the image.

### Integration Tests:

- The `docker-smoke` job is the integration test: real image, real container, real HTTP request.

### Manual Testing Steps:

1. Run the Phase 1 local reproduction commands; confirm `curl /` returns 200 after migrate.
2. Open a PR; confirm `CI / Docker Smoke` runs and passes.
3. Break startup locally (unset `SECRET_KEY` in the run command) and confirm the poll fails with `docker logs` output.
4. After Phase 2, confirm a red smoke check blocks merge and `gh api` lists the new context.

## Performance Considerations

- Adds one image build + short run to CI (~1-2 min). It runs in parallel with `test`/`lint`, so it only extends the
  critical path before `deploy` on master pushes, which is acceptable for a deploy gate.

## Migration Notes

- No data migration. The smoke job migrates only its throwaway SQLite container, which is discarded.

## References

- Research: `context/changes/docker-smoke-test/research.md`
- Test plan: `context/foundation/test-plan.md` (R7, §3 Phase 4, §6)
- Prior CI pattern: `context/archive/2026-06-05-ci-quality-gate/plan.md`
- Workflow: `.github/workflows/ci.yml`
- Dockerfile `CMD`: `Dockerfile:28-33`; health probe: `core/views.py:143-155`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See
> `references/progress-format.md`.

### Phase 1: CI smoke job + deploy gate

#### Automated

- [x] 1.1 Image builds locally: `docker build -t korpotron-smoke:ci .`
- [x] 1.2 Container serves probe locally (run → exec migrate → curl 200 → rm)
- [x] 1.3 Workflow file is valid YAML

#### Manual

- [ ] 1.4 PR shows `CI / Docker Smoke` check passing
- [ ] 1.5 Broken startup makes smoke steps fail with `docker logs` visible
- [ ] 1.6 Deploy does not start until `docker-smoke` passes

### Phase 2: Enforce as required check + close out test plan

#### Automated

- [ ] 2.1 Protection lists `CI / Docker Smoke` in required contexts

#### Manual

- [ ] 2.2 Failing container blocks merge on `CI / Docker Smoke`
- [ ] 2.3 `test-plan.md` §3/§5/§6 updated and consistent
