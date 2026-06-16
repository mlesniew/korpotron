---
project: "Korpotron"
version: 1
created: 2026-06-05
status: active
---

# Test Plan: Korpotron

## §1 Strategy

**Principle 1 — Cost × signal.** Every test added must answer: _what is the cheapest test that gives a real signal for
this risk?_ Do not promote to e2e because it feels safer. Do not layer an AI-native check on top of a deterministic
assertion that already catches the regression.

**Principle 2 — User concerns are evidence.** Risks the team has lived through carry the same weight as PRD lines or
hot-spot data.

**Principle 3 — Risks are scenarios, not code locations.** The risk map in §2 cites evidence (PRD lines, interview
answers, hot-spot directories). It does not assert a specific file as "where the failure lives." That anchor is
`/10x-research`'s output, produced during each rollout phase.

---

## §2 Risk map

| #   | Risk (failure scenario)                                                                                                                    | Impact     | Likelihood | Source(s) — evidence, not anchors                                                                       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ---------- | ------------------------------------------------------------------------------------------------------- |
| R1  | CI gate absent — a broken test merges to master and auto-deploys to prod undetected                                                        | Medium     | High       | CLAUDE.md ("no deploy workflow wired"); roadmap 6 planned slices                                        |
| R2  | IDOR on S-07 JSON endpoints — logged-in user edits or deletes another user's option via the new REST API                                   | High       | Medium     | Roadmap S-07; Interview Q3 (low JS confidence); hot-spot dir `core/`; abuse-lens (Authorization/access) |
| R3  | User registration bypass — S-11 account with `is_active=False` can log in before admin approval                                            | High       | Low-Medium | Roadmap S-11; PRD Access Control; abuse-lens (Authorization/access)                                     |
| R4  | Rate-limit boundary edge cases — generation succeeds beyond the daily cap at the UTC-midnight reset boundary or via concurrent submissions | Medium     | Medium     | Interview Q1; Roadmap S-05; hot-spot dir `core/`                                                        |
| R5  | Prompt injection structural — user-supplied text placed outside the user-message slot, causing system prompt leakage                       | Low-Medium | Low-Medium | Interview Q1; PRD FR-007–FR-011; tech-stack `has_ai: true`                                              |
| R6  | Input non-retention NFR unchecked for future endpoints — S-07/S-11 request payloads inadvertently stored beyond the request                | High       | Low        | PRD NFR ("input text not stored beyond request scope"); Roadmap S-07/S-11                               |
| R7  | Docker container startup failure undetected in CI — image builds but container fails to start or serve HTTP                                | Medium     | Medium     | Interview Q2/Q4; lessons.md ("Verify Docker build before committing")                                   |

**Negative space (do not spend test budget on):**

- Admin panel flows — trusted single admin, low blast radius.
- Django framework internals (built-in auth, ORM) — the framework tests these.
- Misconfiguration scenarios (invalid or missing env var values).

### Risk Response Guidance

| Risk | What would prove protection                                                                                                   | Must challenge                                                                                                              | Context needed (for `/10x-research`)                                                      | Cheapest layer                                                                   | Anti-pattern to avoid                                                                            |
| ---- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| R1   | A PR with a broken test cannot merge to master                                                                                | "We run pytest locally before pushing" — local discipline is not a gate                                                     | GitHub Actions workflow structure; branch protection settings                             | GitHub Actions CI workflow YAML                                                  | CI runs but is not configured as a required check → merges still go through                      |
| R2   | Cross-user request to JSON endpoint returns 404, not 200 with changes applied                                                 | "login_required covers ownership" — login-required ≠ ownership check                                                        | How existing views enforce per-user filtering; S-07 endpoint design                       | Django test client cross-user request                                            | Testing only own-user happy path, never asserting the cross-user rejection                       |
| R3   | `is_active=False` user cannot log in; auth returns a failure, not a redirect into the app                                     | "Django blocks inactive users automatically" — verify this holds for the configured auth backend and any custom login logic | S-11 view implementation; active auth backend; any custom login code path                 | Django test client: register → attempt login without admin approval              | Asserting only that the registration form saves data, not that login is blocked                  |
| R4   | Generation at daily limit + 1 is rejected; limit resets correctly at UTC midnight; `DAILY_GENERATION_LIMIT=0` means unlimited | "select_for_update prevents all races" — verify the lock covers check + increment as one atomic path                        | DailyGenerationCount logic; midnight reset calculation; gaps in existing test coverage    | Django integration tests with mocked `timezone.now()` for boundary               | Testing only the "limit reached" display message, not that the generation call itself is blocked |
| R5   | User-supplied text is in the user-message slot of the LLM prompt array, not the system-message slot                           | "Displaying output verbatim is safe" — verbatim display is the risk, not protection                                         | LLM message construction: which message role carries user content vs. system instructions | Unit test for `build_messages()` verifying content position by role              | Testing LLM refusal behavior (non-deterministic) instead of the structural message array         |
| R6   | After any new endpoint POST, no DB row contains the user-supplied input text                                                  | "generate_creates_no_db_rows already covers this" — that test covers the generate view only, not future endpoints           | Which new S-07/S-11 endpoints accept user-authored text                                   | Pattern check added alongside each new endpoint's test suite                     | Broad "no input in DB" assertion without enumerating which models and fields to check            |
| R7   | Docker image builds; container starts within timeout; health endpoint responds HTTP 200                                       | "Tests pass locally so Docker must work" — local Python env ≠ Docker build + runtime environment                            | Dockerfile contents; health-check URL; required env vars at startup                       | CI shell step: `docker build` → `docker run` → `curl` health check → `docker rm` | Treating Docker success as "build exits 0" without verifying the running container serves HTTP   |

---

## §3 Phased rollout

| #   | Phase name              | Goal                                                                                                                                                                    | Risks covered | Test types                               | Status | Change folder                                    |
| --- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ---------------------------------------- | ------ | ------------------------------------------------ |
| 1   | CI quality gate         | Wire pytest into GitHub Actions; configure as a required check so broken tests block merges to master                                                                   | R1            | GitHub Actions YAML, branch protection   | done   | context/changes/ci-quality-gate/                 |
| 2   | Authorization hardening | Prove ownership isolation for existing endpoint patterns and establish the contract for S-07/S-11 before they ship                                                      | R2, R3        | Django test client integration tests     | done   | context/changes/testing-authorization-hardening/ |
| 3   | LLM & abuse surface     | Prove rate-limit edges are tamper-resistant; verify message construction puts user content in the user-message slot; extend input non-retention checks to new endpoints | R4, R5, R6    | Django integration tests, LLM unit tests | done   | context/changes/rate-limit-testing/              |
| 4   | Docker deployment smoke | CI step that builds the image, starts the container, and verifies the app serves HTTP                                                                                   | R7            | CI shell step                            | done   | context/changes/docker-smoke-test/               |

---

## §4 Stack

**Language / framework:** Python 3.12 · Django 6.0.5 · pytest + pytest-django (configured in `pyproject.toml`)

**Test runner command:** `uv run pytest`

**Test-base profile:** Meaningful — pytest configured; 6 test files, 35+ test functions covering auth, core models,
generation view, LLM message construction, option group views, template views. All tests concentrated in `tests/`.

**Hot-spot scope (last 30 days, 29 commits):**

- Scopes: `core/`, `korpotron/`, `tests/`
- Top files: `korpotron/settings.py` (12 edits), `core/views.py` (11), `tests/test_generate.py` (8)
- Top dirs: `core/` (33), `korpotron/` (28), `tests/` (26), `core/migrations/` (12)
- `core/` is the highest-churn application code directory.

**LLM provider:** OpenRouter via `openai` SDK (`base_url` override). See
`context/foundation/adr/001-llm-provider-openrouter.md`.

**Deployment:** Fly.io · Docker container · GitHub Actions auto-deploy on merge to `master`.

**Stack grounding tools (current session):**

- Docs: Context7 via `npx ctx7@latest` (CLI) — available; not queried this session (Django/pytest tooling is stable);
  checked: 2026-06-05
- Search: WebSearch — available; not queried (no framework version uncertainty)
- Runtime/browser: no Playwright MCP in session — not used
- Provider/platform: no GitHub/Fly.io MCP in session — branch protection and CI configuration verified via CLAUDE.md and
  workflow file inspection during research phases

---

## §5 Existing coverage summary

| Area                                                                                       | Test file                                                                                    | Status                                                                                                 |
| ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Auth (login/logout redirect)                                                               | `tests/test_auth.py`                                                                         | Covered (3 tests)                                                                                      |
| Core models (cascade, creation)                                                            | `tests/test_core_models.py`                                                                  | Covered (6 tests)                                                                                      |
| Generation view (happy path, cross-user, daily limit, error handling, input non-retention) | `tests/test_generate.py`                                                                     | Covered (18 tests)                                                                                     |
| LLM message construction and parsing                                                       | `tests/test_llm.py`                                                                          | Covered (7 tests)                                                                                      |
| Option group views (CRUD, ownership, validation)                                           | `tests/test_option_group_views.py`                                                           | Covered (9 tests)                                                                                      |
| Template views (CRUD, ownership)                                                           | `tests/test_template_views.py`                                                               | Covered (7 tests)                                                                                      |
| CI gate (pytest runs in GitHub Actions, required check on master)                          | `.github/workflows/ci.yml`                                                                   | **Covered** — Phase 1 done                                                                             |
| S-07 JSON endpoint ownership checks                                                        | `tests/test_template_views.py`, `tests/test_option_group_views.py`, `tests/test_generate.py` | Covered — `tests/test_template_views.py`, `tests/test_option_group_views.py`, `tests/test_generate.py` |
| S-11 registration + inactive-user login block                                              | `tests/test_auth.py`                                                                         | **Covered** — Phase 2 done                                                                             |
| Rate-limit midnight boundary + atomic check-and-increment                                  | `tests/test_generate.py` (concurrent boundary tests)                                         | **Covered** — Phase 3 done                                                                             |
| LLM message slot structure (prompt injection structural)                                   | `tests/test_llm.py` (system_message test)                                                    | **Covered** — Phase 3 done                                                                             |
| Input non-retention for future endpoints                                                   | `tests/test_generate.py` (field-value scan)                                                  | **Covered pattern** — Phase 3 done                                                                     |
| Docker build + container startup                                                           | `.github/workflows/ci.yml` (`docker-smoke` job)                                              | **Covered** — Phase 4 done                                                                             |

---

## §6 Cookbook (filled in as phases ship)

### Phase 1 — CI quality gate

**Shipped.** See `context/changes/ci-quality-gate/`.

Pattern — GitHub Actions workflow (`.github/workflows/ci.yml`):

- `test` job: `uv run pytest` with `SECRET_KEY` env var set; triggers on every PR to master and push to master.
- `lint` job: `uv run ruff check .`; parallel to `test`.
- `deploy` job: `needs: [test, lint]`; only runs on push to master.
- Branch protection: `Test` and `Lint` are required status checks on master (`strict: true`). Note: a GitHub Actions
  check context is the job name, not the `CI / <job>` form shown in the PR UI.

Result: a PR with a broken test gets `mergeStateStatus = BLOCKED` — the merge button is disabled until both checks pass.

### Phase 2 — Authorization hardening

**Shipped.** See `context/changes/testing-authorization-hardening/`.

**R2 finding — S-07 IDOR surface (cross-user ownership):**

S-07 produced no REST JSON endpoints; the anticipated IDOR surface was designed away (all data access goes through
template/option-group views, not a REST API — see `context/foundation/roadmap.md:228`). Six cross-user rejection tests
already existed across template, option-group, and generate views before Phase 2 opened — no new tests were needed.
Note: the `generate` view returns HTTP 400 (not 404/403) for cross-user violations. This is intentional — the endpoint
accepts JSON and returns an error-key response. The behavior is tested and correct; normalizing to 403/404 would change
existing tests with no security benefit.

**R3 pattern — inactive-user login block:**

- `@pytest.mark.django_db` function (no `transaction=True` needed).
- Inactive user created inline: `User.objects.create_user(username="inactive", password="pass1234", is_active=False)`.
  Do not use a shared fixture — test-specific state keeps the test self-contained.
- POST valid credentials to `/accounts/login/`.
- Two assertions required: `response.status_code == 200` (form re-rendered, not redirected) **and**
  `not response.wsgi_request.user.is_authenticated` (HTTP 200 alone could be a successful login to a redirect-free
  page).
- No custom auth backend override exists in this project; the test pins the Django-default `ModelBackend` +
  `AuthenticationForm.confirm_login_allowed()` chain.

### Phase 3 — LLM & abuse surface

**Shipped.** See `context/changes/rate-limit-testing/`.

Pattern — Rate-limit boundaries (R4):

- Two threading-based concurrency tests (`transaction=True` marker) using `Barrier` to synchronize thread entry into the
  critical section.
- One test at an existing-row boundary (`count = limit - 1`), one at first-of-day (no pre-existing row).
- Each asserts `sorted(statuses) == [200, 429]` (one request succeeds, one is rate-limited) and final DB count matches
  limit.
- Requires SQLite `transaction_mode = IMMEDIATE` in settings to enable row-level locking (Django 6.x dropped DEFERRED
  mode support).

Pattern — Prompt injection structural (R5):

- Unit test `test_build_messages_user_text_absent_from_system_message` verifies user input text is absent from
  `messages[0]["content"]` (the system-message slot).
- Negative assertion: if `build_messages()` were modified to embed user text in system prompt, this test catches it.

Pattern — Input non-retention (R6):

- Existing `test_generate_creates_no_db_rows` strengthened with a field-value scan.
- Iterates over all Template, OptionGroup, and Option instances and their CharField/TextField fields, asserting none
  contain the literal input string `"rewrite me"`.
- Docstring marks it as the R6 pattern contract for future endpoints (S-07, S-11).

### Phase 4 — Docker deployment smoke

**Shipped.** See `context/changes/docker-smoke-test/`.

Pattern — Docker smoke CI job (R7):

- `docker-smoke` job: parallel to `test`/`lint`; runs on every PR and push to master.
- Steps: `docker build -t korpotron-smoke:ci .` →
  `docker run -d -p 8080:8080 -e SECRET_KEY=... -e ALLOWED_HOSTS=localhost,127.0.0.1 --name korpotron-smoke` →
  `docker exec korpotron-smoke python manage.py migrate --noinput` → poll `curl http://localhost:8080/` until HTTP 200
  or 30s timeout → teardown with `docker rm -f` (always runs).
- On timeout: prints `docker logs korpotron-smoke` before failing.
- `deploy` job: `needs: [test, lint, docker-smoke]` — deploy is blocked until the smoke check passes.
- Branch protection: `Docker Smoke` added as a required status check on master.

Result: a PR whose container fails to start or serve HTTP gets `mergeStateStatus = BLOCKED`.

---

## §7 Refresh cadence

Re-run `/10x-test-plan --refresh` when:

- A new top-3 risk surfaces (new planned slice with auth or LLM surface).
- A stack grounding tool's `checked:` date is > 3 months old.
- The tech stack changes (new LLM provider, move from SQLite to Postgres in prod, added background job framework).
- The negative space in §2 no longer matches what is accepted: e.g., if admin access is extended to non-trusted users,
  admin flows are no longer negative space.
