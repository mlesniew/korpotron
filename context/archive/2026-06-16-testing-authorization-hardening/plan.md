# Authorization Hardening — Phase 2 Implementation Plan

## Overview

Add one test proving that Django's `ModelBackend` blocks inactive users from logging in (R3), then update the test-plan
documentation to reflect R2 is already covered by existing tests and R3 is now covered.

## Current State Analysis

Research confirmed:

- **R2 (IDOR on fetch endpoints)** is already fully covered. Six cross-user rejection tests exist across
  `tests/test_template_views.py`, `tests/test_option_group_views.py`, and `tests/test_generate.py`. The test-plan §5
  entry saying "Not covered → Phase 2" was written before those tests were added.
- **R3 (inactive-user login block)** has a genuine gap. No test currently verifies that `is_active=False` prevents login
  through `ModelBackend`. The `AuthenticationForm.confirm_login_allowed()` re-renders the form with HTTP 200 for
  inactive users; this chain is untested.
- `tests/test_auth.py` already covers valid login (redirect), invalid credentials (form re-render), and logout. It has
  no inactive-user case.
- `context/foundation/test-plan.md §5` has two stale rows (R2 and R3 both say "Not covered → Phase 2"); §6 has a "TBD"
  placeholder for the Phase 2 cookbook.

### Key Discoveries:

- `tests/test_auth.py:1-32` — existing test file; imports `User`, `Client`; no `is_active=False` test
- `tests/conftest.py:17-24` — `user` fixture creates `tester / pass1234`; inactive-user test needs no shared fixture
  (test-specific inline user)
- `core/views.py:36-51` — `RegisterView` calls `form.save()` → Django `create_user()` → `is_active=True` by default; no
  override
- `korpotron/urls.py:22` — login via `include("django.contrib.auth.urls")`; no custom auth backend
- `context/foundation/test-plan.md:111-112` — stale §5 rows for R2 and R3
- `context/foundation/test-plan.md:138` — §6 Phase 2 section is "TBD"
- `context/foundation/test-plan.md:62` — §3 Phase 2 row status is "change opened"

## Desired End State

`tests/test_auth.py` contains `test_inactive_user_cannot_login`, which proves:

1. A POST to `/accounts/login/` with valid credentials for an `is_active=False` user returns HTTP 200 (not redirect).
2. The user's session is not authenticated after the attempt.

`context/foundation/test-plan.md` §5 coverage table is accurate: R2 rows reference the existing cross-user tests; R3 row
references `tests/test_auth.py`. §6 Phase 2 cookbook documents R2 findings and the R3 pattern.

## What We're NOT Doing

- **No normalization of generate endpoint's 400 response.** The `generate` view returns HTTP 400 (not 404/403) for
  cross-user violations. This is intentional: the endpoint accepts JSON and returns an error-key response. The behavior
  is tested and correct; normalizing it would change existing tests with no security benefit.
- **No control-group test for active-user login success.** `test_valid_login_redirects_to_home` already covers this in
  the same file.
- **No changes to the registration flow.** S-11 creates active users by design; `is_active=True` is the correct
  production default. The R3 test proves the login-block mechanism works for any future scenario that sets
  `is_active=False`.
- **No new cross-user tests for R2.** All six cross-user rejection tests that satisfy R2 already exist.

## Implementation Approach

Phase 1 adds the one missing test; Phase 2 updates the living documentation. Both changes are independent and low-risk —
no production code is touched.

---

## Phase 1: R3 Test — Inactive-User Login Block

### Overview

Add `test_inactive_user_cannot_login` to `tests/test_auth.py`. This test creates an inactive user inline (no shared
fixture), POSTs valid credentials to the login endpoint, and asserts both that the response is HTTP 200 (form
re-rendered, not redirected) and that the session is not authenticated.

### Changes Required:

#### 1. Add inactive-user login test

**File**: `tests/test_auth.py`

**Intent**: Prove that `ModelBackend` + `AuthenticationForm.confirm_login_allowed()` blocks login for users with
`is_active=False`. This establishes the contract so any future custom auth backend or login-path change must explicitly
preserve it.

**Contract**: New `@pytest.mark.django_db` function (no `transaction=True` needed). Creates the inactive user inline:
`User.objects.create_user(username="inactive", password="pass1234", is_active=False)`. POSTs to `/accounts/login/` with
those credentials. Asserts `response.status_code == 200` and `not response.wsgi_request.user.is_authenticated` — both
assertions are required because HTTP 200 alone could be a successful login to a redirect-free page.

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_auth.py -v` — all 4 tests pass (3 existing + 1 new)
- `uv run pytest` — full suite passes with no regressions
- `uv run ruff check .` — no lint errors

#### Manual Verification:

- No manual verification required for a pure test addition.

**Implementation Note**: No manual gate needed before Phase 2 — proceed directly after all automated checks pass.

---

## Phase 2: Test-Plan Documentation

### Overview

Update `context/foundation/test-plan.md` to reflect the true state of Phase 2 coverage: correct §5 stale rows for R2 and
R3, fill in the §6 Phase 2 cookbook, and mark the §3 Phase 2 row as done.

### Changes Required:

#### 1. Update §5 coverage table — R2 row

**File**: `context/foundation/test-plan.md`

**Intent**: Replace the stale "Not covered → Phase 2" entry for R2 with an accurate covered status referencing the three
test files that contain cross-user rejection tests.

**Contract**: §5 table row for "S-07 JSON endpoint ownership checks": change the `Status` cell from
`**Not covered** → Phase 2` to `Covered — \`tests/test_template_views.py\`, \`tests/test_option_group_views.py\`,
\`tests/test_generate.py\``. Update the `Test file`cell from`—` to those three paths.

#### 2. Update §5 coverage table — R3 row

**File**: `context/foundation/test-plan.md`

**Intent**: Replace the stale "Not covered → Phase 2" entry for R3 with an accurate covered status referencing the new
test.

**Contract**: §5 table row for "S-11 registration + inactive-user login block": change `Status` from
`**Not covered** → Phase 2` to `**Covered** — Phase 2 done`. Update `Test file` from `—` to `tests/test_auth.py`.

#### 3. Fill in §6 Phase 2 Cookbook

**File**: `context/foundation/test-plan.md`

**Intent**: Replace the "TBD" Phase 2 cookbook placeholder with the patterns established by this change, for future
reference when writing similar tests.

**Contract**: Replace the paragraph beginning "TBD — see §3 Phase 2" with a filled-in cookbook section covering:

- **R2 finding**: S-07 produced no REST endpoints (per `context/foundation/roadmap.md:228`); anticipated IDOR surface
  was designed away; six cross-user tests already existed across template, option-group, and generate views before Phase
  2 opened. Note: `generate` returns HTTP 400 (not 404/403) for cross-user violations — intentional, not a gap.
- **R3 pattern**: `@pytest.mark.django_db` test; inactive user created inline (not via shared fixture — test-specific
  state); POST to `/accounts/login/`; double assertion on status code (200) and session auth state (not authenticated).
  No custom auth backend override exists in this project; the test pins the Django-default chain.

#### 4. Update §3 Phase 2 row status

**File**: `context/foundation/test-plan.md`

**Intent**: Mark the §3 rollout table row for Phase 2 as done.

**Contract**: §3 Phase 2 table row: change status cell from `change opened` to `done`. Add reference to this change
folder.

### Success Criteria:

#### Automated Verification:

- `uv run pytest` — suite still passes (no test files were modified in Phase 2)
- `uv run ruff check .` — still passes

#### Manual Verification:

- §5 table R2 row references the three test files and shows "Covered" (not "Not covered → Phase 2")
- §5 table R3 row references `tests/test_auth.py` and shows "Covered — Phase 2 done"
- §6 Phase 2 cookbook section contains R2 findings and R3 pattern (no "TBD" remaining)
- §3 Phase 2 row shows "done"

---

## Testing Strategy

### Unit Tests:

- `test_inactive_user_cannot_login`: verifies HTTP 200 response and unauthenticated session state for `is_active=False`
  user with valid credentials

### Integration Tests:

- N/A — the new test is itself a Django test-client integration test against the full login view stack

### Manual Testing Steps:

1. Run `uv run pytest tests/test_auth.py -v` and confirm 4 green tests
2. Run `uv run pytest` and confirm no regressions
3. Open `context/foundation/test-plan.md` and verify §5 R2 and R3 rows are accurate

## References

- Research: `context/changes/testing-authorization-hardening/research.md`
- Test-plan: `context/foundation/test-plan.md`
- Existing cross-user tests: `tests/test_template_views.py:71-89`, `tests/test_option_group_views.py:112-129`,
  `tests/test_generate.py:179-198`
- Existing auth tests: `tests/test_auth.py`
- Lessons: `context/foundation/lessons.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See
> `references/progress-format.md`.

### Phase 1: R3 Test — Inactive-User Login Block

#### Automated

- [x] 1.1 `uv run pytest tests/test_auth.py -v` — all 4 tests pass — 627cb6d
- [x] 1.2 `uv run pytest` — full suite passes with no regressions — 627cb6d
- [x] 1.3 `uv run ruff check .` — no lint errors — 627cb6d

### Phase 2: Test-Plan Documentation

#### Automated

- [x] 2.1 `uv run pytest` — suite still passes — 2434c52
- [x] 2.2 `uv run ruff check .` — still passes — 2434c52

#### Manual

- [x] 2.3 §5 R2 row references three test files and shows Covered — 2434c52
- [x] 2.4 §5 R3 row references `tests/test_auth.py` and shows Covered — Phase 2 done — 2434c52
- [x] 2.5 §6 Phase 2 cookbook section is filled in (no TBD remaining) — 2434c52
- [x] 2.6 §3 Phase 2 row shows done — 2434c52
