# Authorization Hardening — Plan Brief

> Full plan: `context/changes/testing-authorization-hardening/plan.md` Research:
> `context/changes/testing-authorization-hardening/research.md`

## What & Why

Add one test that proves Django's `ModelBackend` blocks login for `is_active=False` users (R3), and correct the
test-plan documentation where R2 was marked "Not covered" but tests already exist. This is Phase 2 of the test rollout
plan — establishing the ownership-isolation and inactive-user contracts before any future auth flow changes.

## Starting Point

`tests/test_auth.py` has 3 tests (valid login, invalid credentials, logout). No test covers the inactive-user case. The
test-plan §5 coverage table has two stale rows: R2 says "Not covered → Phase 2" even though 6 cross-user tests exist
across template, option-group, and generate views; R3 correctly says uncovered.

## Desired End State

`tests/test_auth.py` gains `test_inactive_user_cannot_login`, proving the `ModelBackend` blocks inactive users with a
double assertion (HTTP 200 + unauthenticated session). The test-plan §5 table is accurate, §6 has the Phase 2 cookbook
filled in, and §3 marks Phase 2 done.

## Key Decisions Made

| Decision                     | Choice                      | Why (1 sentence)                                                                                           | Source   |
| ---------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------- | -------- |
| R2 new tests                 | None needed                 | Six cross-user rejection tests already exist; the risk was designed away when S-07 chose no REST endpoints | Research |
| Generate endpoint 400 status | Leave as-is                 | HTTP 400 with error key is correct for a JSON endpoint; no unauthorized data returned                      | Plan     |
| test-plan §5 update          | Yes — correct both rows     | Stale "Not covered" entries would mislead future readers about R2 coverage                                 | Plan     |
| R3 test user                 | Inline creation, no fixture | Inactive user is test-specific state; the `user` fixture is always active                                  | Research |
| Control-group test           | Skip                        | `test_valid_login_redirects_to_home` already covers active-user success                                    | Plan     |

## Scope

**In scope:**

- One new test: `test_inactive_user_cannot_login` in `tests/test_auth.py`
- test-plan §5 table: R2 and R3 rows corrected
- test-plan §6: Phase 2 cookbook filled in
- test-plan §3: Phase 2 row marked done

**Out of scope:**

- Changes to production code (no views, models, or URLs modified)
- Normalizing generate endpoint to return 404/403 (deliberate 400 left unchanged)
- New cross-user tests (R2 already fully covered)
- Registration flow changes

## Architecture / Approach

Pure test addition and documentation correction. Phase 1 adds one `@pytest.mark.django_db` test that creates an inactive
user inline and POSTs to Django's built-in login view. Phase 2 edits the living test-plan document to reflect truth. No
migration, no schema change, no production code touched.

## Phases at a Glance

| Phase             | What it delivers                                                     | Key risk                                                 |
| ----------------- | -------------------------------------------------------------------- | -------------------------------------------------------- |
| 1. R3 Test        | `test_inactive_user_cannot_login` — inactive-user login block proven | None significant; test follows established patterns      |
| 2. Test-Plan Docs | §5 accurate, §6 cookbook filled, §3 marked done                      | Editing test-plan.md carefully to not disturb other rows |

**Prerequisites:** None — no branch or migration dependency. **Estimated effort:** ~1 session, 2 phases (trivial
implementation).

## Open Risks & Assumptions

- The `generate` endpoint's HTTP 400 response for cross-user violations is intentional and documented as such. If HTTP
  semantics are ever standardized, that's a separate change.
- R2 coverage depends on tests added after the test-plan was authored; this plan documents that finding but does not
  change those tests.

## Success Criteria (Summary)

- `uv run pytest` passes with 4 green tests in `test_auth.py` and no regressions in the full suite
- `context/foundation/test-plan.md §5` shows "Covered" for both R2 and R3 rows
- §6 Phase 2 cookbook is no longer "TBD"
