# CI Quality Gate — Plan Brief

> Full plan: `context/changes/ci-quality-gate/plan.md`

## What & Why

Wire pytest and ruff check into GitHub Actions so that broken tests and lint failures block both PR merges and Fly.io deployments. This addresses R1 from the test plan: the current repo has no CI gate — a broken test can merge to master and auto-deploy undetected.

## Starting Point

One workflow exists (`.github/workflows/deploy.yml`) that triggers only on push to master and only deploys. There is no test or lint step anywhere in CI. The test suite (`uv run pytest`, 35+ tests) runs fine locally but nothing enforces it before code ships.

## Desired End State

Every PR targeting master triggers two parallel GitHub Actions checks — `CI / Test` and `CI / Lint`. The deploy job depends on both and only runs on pushes to master. Branch protection on master marks both checks as required, making it mechanically impossible to merge a PR until they pass.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| CI trigger | `push` to master + `pull_request` targeting master | Catches both PR merges and rare direct pushes | Plan |
| Test and lint as separate jobs | Yes — parallel jobs | Immediately visible which check failed; no extra cost | User |
| Deploy depends on CI | `needs: [test, lint]` in the same workflow | Atomic — deploy never runs if CI failed on the same push | User |
| Old `deploy.yml` | Delete it | Deploy moves to `ci.yml`; keeping both causes a duplicate unconditional deploy | Plan |
| Branch protection setup | Run `gh api` command during implementation | Reproducible and verifiable; one-time admin operation | User |
| `enforce_admins` | `false` | Keeps admin bypass available for emergency hotfixes | Plan |
| Linting scope | `ruff check .` only | `ruff format --check` deferred; mypy deferred (CLAUDE.md notes it's not yet wired) | Plan |

## Scope

**In scope:**
- New `.github/workflows/ci.yml` with `test`, `lint`, `deploy` jobs
- Deletion of `.github/workflows/deploy.yml`
- Branch protection on master requiring `CI / Test` and `CI / Lint`

**Out of scope:**
- `ruff format --check` in CI
- mypy type checking in CI
- CI on feature branches beyond PRs targeting master
- `enforce_admins: true` branch protection

## Architecture / Approach

Single workflow file `ci.yml` triggered by `push` to master and `pull_request` targeting master. `test` and `lint` jobs run in parallel on every trigger. A `deploy` job carries `needs: [test, lint]` and an `if:` guard limiting it to push-to-master events only. `astral-sh/setup-uv` installs uv + Python 3.12 in each job. `SECRET_KEY` is set to a dummy value in the `test` job env (required by Django settings; any non-empty string suffices for tests).

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. CI workflow | `ci.yml` with test, lint, deploy; `deploy.yml` deleted | `astral-sh/setup-uv` action version may need verification against current GitHub Marketplace |
| 2. Branch protection | Master requires `CI / Test` + `CI / Lint` to pass | Context names must exactly match what GitHub shows after the first CI run |

**Prerequisites:** Phase 2 must run after Phase 1 is merged to master and has at least one completed CI run (so GitHub has registered the check names).
**Estimated effort:** ~1 session across 2 phases.

## Open Risks & Assumptions

- The `astral-sh/setup-uv@v6` version tag is assumed current — verify against GitHub Marketplace before committing.
- Branch protection context strings (`"CI / Test"`, `"CI / Lint"`) must exactly match the names GitHub assigns after the first run; if the workflow name changes, these strings need updating.

## Success Criteria (Summary)

- A PR with a broken test cannot be merged to master — GitHub shows the merge button disabled.
- A push to master that passes CI triggers a Fly.io deploy; a push that fails CI does not.
- `gh api` branch protection query confirms both check names are in `required_status_checks.contexts`.
