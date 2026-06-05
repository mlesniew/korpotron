# CI Quality Gate — Implementation Plan

## Overview

Wire pytest and ruff check into GitHub Actions as two parallel jobs. The deploy job depends on both so that a failing test or lint violation stops the deployment. Configure master's branch protection to require both checks to pass before any PR can merge.

## Current State Analysis

One workflow exists: `.github/workflows/deploy.yml`. It triggers only on `push` to master and only deploys — no test or lint step. There is no CI gate. A PR with a broken test can be merged and will auto-deploy to Fly.io.

Tests run via `uv run pytest`; `pytest-django` is configured in `pyproject.toml` with `DJANGO_SETTINGS_MODULE = "korpotron.settings"`. `ruff` is in dev deps. `SECRET_KEY` is a required env var with no default — the workflow must supply a dummy value.

## Desired End State

Two GitHub Actions jobs (`CI / Test`, `CI / Lint`) run in parallel on every PR targeting master and every push to master. A third `deploy` job gates on both. Branch protection on master marks both as required checks, making it impossible to merge a PR until they pass. To verify: open a PR with a deliberately broken test and confirm GitHub blocks the merge button.

### Key Discoveries

- `SECRET_KEY = os.environ["SECRET_KEY"]` — no default; CI must set this env var.
- `OPENROUTER_API_KEY` is optional; tests that mock the LLM need no API key.
- `DATABASE_URL` defaults to SQLite when unset; CI needs no database setup.
- `deploy.yml` currently has no `needs:` — deploy fires even if tests would fail (on master push there are currently no test jobs).

## What We're NOT Doing

- Not adding `ruff format --check` (lint job is `ruff check` only).
- Not enabling `enforce_admins: true` on branch protection — admin bypass is kept available for emergency hotfixes.
- Not running CI on feature branches other than via PRs targeting master.
- Not adding mypy to the CI gate (CLAUDE.md notes mypy is "to be wired into CI" — deferred).

## Implementation Approach

Replace `deploy.yml` with a single `ci.yml` that declares all three jobs. Fold the existing deploy steps in verbatim. The `if:` condition on the deploy job limits it to `push` events on master. Branch protection is applied via `gh api` once the workflow is merged to master and has produced at least one run (so GitHub has seen the check names).

---

## Phase 1: GitHub Actions CI workflow

### Overview

Create `.github/workflows/ci.yml` with `test`, `lint`, and `deploy` jobs. Remove `.github/workflows/deploy.yml`.

### Changes Required

#### 1. New CI workflow

**File**: `.github/workflows/ci.yml`

**Intent**: Define the full CI/CD pipeline — parallel test and lint jobs that run on every PR to master and every push to master, with a deploy job that runs only on push to master and requires both to pass.

**Contract**: The workflow name must be `CI` (this determines the check context name prefix, e.g. `CI / Test`, `CI / Lint`, which is what branch protection references). The deploy job must carry `needs: [test, lint]` and `if: github.event_name == 'push' && github.ref == 'refs/heads/master'`. The `test` job must set `SECRET_KEY` to any non-empty string in its `env:`. The `astral-sh/setup-uv` action installs uv and Python 3.12; use `enable-cache: true`. Pin `superfly/flyctl-actions/setup-flyctl` to a specific release tag (not `@master`) — check the current tag at https://github.com/superfly/flyctl-actions/releases before committing.

```yaml
name: CI

on:
  push:
    branches:
      - master
  pull_request:
    branches:
      - master

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          python-version: "3.12"
      - run: uv run pytest
        env:
          SECRET_KEY: ci-placeholder-not-used-in-production

  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          python-version: "3.12"
      - run: uv run ruff check .

  deploy:
    name: Deploy
    needs: [test, lint]
    if: github.event_name == 'push' && github.ref == 'refs/heads/master'
    runs-on: ubuntu-latest
    concurrency:
      group: fly-deploy
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@v0.0.3  # pin to current release — verify before committing
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

#### 2. Remove old deploy workflow

**File**: `.github/workflows/deploy.yml`

**Intent**: Delete this file. Its deploy step is now covered by the `deploy` job in `ci.yml`; keeping both would result in a duplicate unconditional deploy on every master push.

### Success Criteria

#### Automated Verification

- `uv run pytest` passes locally
- `uv run ruff check .` passes locally
- `.github/workflows/deploy.yml` no longer exists
- `.github/workflows/ci.yml` exists and is valid YAML
- `astral-sh/setup-uv@v6` is the current major release (verified on GitHub Marketplace)

#### Manual Verification

- Push the branch to GitHub and open a PR targeting master; confirm two check runs appear: `CI / Test` and `CI / Lint`
- Both checks pass on the PR before merging

---

## Phase 2: Branch protection

### Overview

Configure master's branch protection rules via `gh api` to require the `CI / Test` and `CI / Lint` checks to pass before a PR can merge. This must run after Phase 1 has been merged to master and at least one CI run has completed (so GitHub has registered the check names).

### Changes Required

#### 1. Apply branch protection via gh CLI

**File**: n/a — a one-time `gh api` command, not a file change.

**Intent**: Set required status checks on master so that GitHub blocks PR merges until `CI / Test` and `CI / Lint` both report green. Run this command from any checkout of the repo with admin rights.

**Contract**: The check context names must exactly match the strings GitHub shows on PR check runs — `"CI / Test"` and `"CI / Lint"` (workflow name + space + slash + space + job name). `strict: true` requires the branch to be up to date with master before merging.

```bash
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')
gh api "repos/$REPO/branches/master/protection" \
  --method PUT \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI / Test", "CI / Lint"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
EOF
```

### Success Criteria

#### Automated Verification

- `gh api repos/$(gh repo view --json nameWithOwner -q '.nameWithOwner')/branches/master/protection` returns a JSON object where `required_status_checks.contexts` contains `"CI / Test"` and `"CI / Lint"`

#### Manual Verification

- Open a PR with a deliberately broken test; confirm GitHub shows the merge button disabled with "Required status checks have not passed"

---

## Testing Strategy

### Automated

- Existing `uv run pytest` suite (35+ tests) must stay green after the workflow file addition — no logic changes, only CI config.
- `uv run ruff check .` must pass clean on the final branch.

### Manual Testing Steps

1. Push the feature branch, open a PR to master — confirm `CI / Test` and `CI / Lint` appear as pending/running checks.
2. Wait for both to pass — confirm the merge button becomes available.
3. Create a throwaway branch with a broken test (`assert False`), open a PR — confirm both checks run and Test shows red; merge button disabled.
4. After merging Phase 1 and applying branch protection (Phase 2), repeat step 3 to confirm protection is active.

## References

- Test plan risk R1: `context/foundation/test-plan.md` §2
- Existing deploy workflow: `.github/workflows/deploy.yml`
- uv setup action: `astral-sh/setup-uv` (GitHub Marketplace)

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: GitHub Actions CI workflow

#### Automated

- [x] 1.1 `uv run pytest` passes locally
- [x] 1.2 `uv run ruff check .` passes locally
- [x] 1.3 `.github/workflows/deploy.yml` no longer exists
- [x] 1.4 `.github/workflows/ci.yml` exists and is valid YAML
- [x] 1.5 `astral-sh/setup-uv@v6` is the current major release (verified on GitHub Marketplace)

#### Manual

- [x] 1.6 PR shows `CI / Test` and `CI / Lint` check runs — 84b0505
- [x] 1.7 Both checks pass on the PR before merging — 84b0505

### Phase 2: Branch protection

#### Automated

- [x] 2.1 `gh api` returns protection with `CI / Test` and `CI / Lint` in required contexts

#### Manual

- [x] 2.2 PR with broken test shows merge button disabled with required-checks message
