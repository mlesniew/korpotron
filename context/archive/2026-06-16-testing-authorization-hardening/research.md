---
date: 2026-06-16T13:41:55+02:00
researcher: Michał Leśniewski
git_commit: cc9da568be780304e1b28f22850463236c59ef53
branch: master
repository: korpotron
topic: "Authorization hardening — ownership isolation tests for JSON endpoints and inactive-user login block"
tags: [research, codebase, authorization, idor, authentication, registration, ownership]
status: complete
last_updated: 2026-06-16
last_updated_by: Michał Leśniewski
---

# Research: Authorization Hardening (Phase 2)

**Date**: 2026-06-16T13:41:55+02:00 **Researcher**: Michał Leśniewski **Git Commit**:
cc9da568be780304e1b28f22850463236c59ef53 **Branch**: master **Repository**: korpotron

## Research Question

What needs to be implemented for Phase 2 of the test plan — ownership isolation tests for JSON/fetch endpoints (R2) and
the inactive-user login block test (R3)?

## Summary

**R2 (IDOR on JSON/fetch endpoints)** is already covered by existing cross-user tests that were added after the
test-plan §5 coverage table was written. S-07 was explicitly designed with "No REST endpoints", so no new JSON API was
ever added; the only fetch-style endpoints are the 204-returning DELETE views and `/generate/`, all of which already
have cross-user rejection tests.

**R3 (inactive-user login block)** has a genuine gap: no test currently verifies that a user with `is_active=False`
cannot log in. The S-11 registration creates active users by design, but the contract that `ModelBackend` actually
blocks inactive users is not asserted anywhere. One new test in `tests/test_auth.py` covers this.

---

## Detailed Findings

### R2 — IDOR on JSON/Fetch Endpoints

#### S-07 produced no REST endpoints

Roadmap S-07 (`option-group-edit-ux`) explicitly states in `context/foundation/roadmap.md:228-229`:

> "No REST endpoints — existing Django formset POST unchanged." "Vanilla JS only — replaces the raw Django formset
> DELETE checkbox with a visible Delete button that checks the hidden checkbox and hides the row."

This means the anticipated "new REST API" risk never materialized. The anticipated R2 risk (IDOR on S-07 REST endpoints)
was designed away.

#### Fetch-callable endpoints that exist today

There are three categories of endpoints called from the frontend without a full page reload:

| Endpoint                           | View                    | Response                   | Ownership guard                                                                                                                 |
| ---------------------------------- | ----------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `POST /templates/<pk>/delete/`     | `TemplateDeleteView`    | `HttpResponse(status=204)` | `get_queryset()` filters `user=request.user` → 404 on IDOR                                                                      |
| `POST /option-groups/<pk>/delete/` | `OptionGroupDeleteView` | `HttpResponse(status=204)` | `get_queryset()` filters `user=request.user` → 404 on IDOR                                                                      |
| `POST /generate/`                  | `generate` (function)   | `JsonResponse`             | `Template.objects.filter(user=request.user, pk=...)` → 400; `Option.objects.filter(group__user=request.user, pk__in=...)` → 400 |

Source: `core/views.py:80-90` (TemplateDeleteView), `core/views.py:156-166` (OptionGroupDeleteView),
`core/views.py:184-276` (generate).

#### Cross-user tests that already exist

| Test                                              | File:line                                  | Assertion               |
| ------------------------------------------------- | ------------------------------------------ | ----------------------- |
| `test_template_update_other_user_returns_404`     | `tests/test_template_views.py:71-80`       | 404                     |
| `test_template_delete_other_user_returns_404`     | `tests/test_template_views.py:83-89`       | 404                     |
| `test_option_group_update_other_user_returns_404` | `tests/test_option_group_views.py:112-120` | 404                     |
| `test_option_group_delete_other_user_returns_404` | `tests/test_option_group_views.py:123-129` | 404                     |
| `test_generate_cross_user_template_rejected`      | `tests/test_generate.py:179-186`           | 400 + `"error"` in JSON |
| `test_generate_cross_user_option_rejected`        | `tests/test_generate.py:189-198`           | 400 + `"error"` in JSON |

The test-plan §5 said "S-07 JSON endpoint ownership checks — Not covered → Phase 2" because it was written (2026-06-05)
before the cross-user tests for template and option-group views were added (those commits post-date the test-plan
authoring). The current codebase has these tests.

#### Status code note for generate endpoint

The generate view returns HTTP 400 (not 403/404) for cross-user ownership violations on templates and options. This is
intentional: the view uses a generic "not found" business error rather than an HTTP authorization code. This is a minor
convention inconsistency but not a security gap — no unauthorized data is returned or modified.

#### R2 verdict

**R2 is already covered.** No new tests are needed for this risk. Phase 2 should confirm this by running the suite and
documenting the finding.

---

### R3 — Inactive-User Login Block

#### S-11 creates active users

The roadmap is explicit — `context/foundation/roadmap.md:249`:

> "Accounts are immediately active — no admin approval step."

The registration view (`core/views.py:36-51`) calls `form.save()` which delegates to `UserCreationForm.save()` which
calls `User.objects.create_user()`. Django's `create_user()` sets `is_active=True` by default. No override exists
anywhere in the registration path.

Confirmed by existing test at `tests/test_registration.py:59-77`:

```python
user = User.objects.filter(username="newuser").first()
assert user is not None
assert user.is_active  # True — user is immediately active
```

#### Auth backend

No `AUTHENTICATION_BACKENDS` is set in `korpotron/settings.py`. Django's default `ModelBackend` is used. The login
endpoint is Django's built-in `LoginView`, included at `korpotron/urls.py:22`:

```python
path("accounts/", include("django.contrib.auth.urls")),
```

#### Django ModelBackend behavior for inactive users

Django's `ModelBackend.authenticate()` (via `_check_password`) returns `None` for users with `is_active=False`. The
`AuthenticationForm.confirm_login_allowed()` also raises a `ValidationError` with code `inactive` and the message "This
account is inactive." — ensuring the login form re-renders with 200 rather than redirecting.

#### What is currently NOT tested

No test verifies:

- That `is_active=False` prevents login through the `ModelBackend`
- That a call to `POST /accounts/login/` with valid credentials for an inactive user returns 200 (not 302)
- That the user's session is not authenticated after the failed login

The test-plan §5 row "S-11 registration + inactive-user login block — Not covered → Phase 2" accurately reflects this
gap.

#### R3 verdict

**One new test is needed.** It does not require the registration flow to set `is_active=False` — it can create the
inactive user directly. The test establishes the contract: if the registration flow is ever changed to require admin
approval, the login-block mechanism is already proven to work.

---

## Code References

- `core/views.py:36-51` — `RegisterView`: form-based registration, no `is_active` override
- `core/views.py:80-90` — `TemplateDeleteView`: `get_queryset()` scoped to `user=request.user`, returns 204 on success
- `core/views.py:84-86` — `TemplateDeleteView.get_queryset()`: `Template.objects.filter(user=self.request.user)`
- `core/views.py:156-166` — `OptionGroupDeleteView`: same 204 + ownership pattern
- `core/views.py:184-276` — `generate()`: ownership via `.filter(user=request.user, pk=...)`, returns 400 on cross-user
- `core/views.py:211-214` — Template ownership filter:
  `Template.objects.filter(user=request.user, pk=template_id).first()`
- `core/views.py:224-232` — Option ownership filter:
  `Option.objects.filter(group__user=request.user, pk__in=option_ids)`
- `tests/conftest.py:17-24` — `user` and `other_user` fixtures
- `tests/test_template_views.py:71-89` — existing cross-user rejection tests for templates
- `tests/test_option_group_views.py:112-129` — existing cross-user rejection tests for option groups
- `tests/test_registration.py:59-77` — confirms registration creates `is_active=True` users
- `korpotron/urls.py:22` — login via `include("django.contrib.auth.urls")`
- `context/foundation/roadmap.md:228` — S-07 "No REST endpoints" decision
- `context/foundation/roadmap.md:249` — S-11 "accounts are immediately active"

## Architecture Insights

**Ownership pattern**: All pk-parameterized views guard ownership by overriding `get_queryset()` to filter
`user=self.request.user`. Django's `UpdateView`/`DeleteView` automatically call `get_queryset()` before fetching by pk,
so a cross-user pk simply returns a 404 from the ORM — no custom 403 logic needed. This pattern is consistent across all
views.

**Generate endpoint exception**: The function-based `generate` view uses `.filter(user=request.user, pk=...).first()`
and returns 400 on None rather than 404. This is correct behavior (the endpoint accepts JSON, so returning 400 with an
error key fits its contract), but differs from the 404 pattern used by the class-based views.

**`is_active` relies on Django internals**: The inactive-user login block is enforced entirely by `ModelBackend` and
`AuthenticationForm.confirm_login_allowed()`, neither of which are overridden in this codebase. The test must verify
this chain explicitly so that any future custom auth backend would need to preserve the behavior.

## Historical Context (from prior changes)

- `context/archive/2026-06-08-option-group-edit-ux/` — S-07: explicitly chose no REST endpoints to avoid IDOR surface
- `context/archive/2026-06-15-user-registration/` — S-11: accounts immediately active, passphrase-only gate
- `context/changes/testing-authorization-hardening/change.md` — R2/R3 risk framing

## Plan Implications

### For the test implementation

**R2 — No new tests needed.** Confirm existing cross-user tests pass and document as Phase 2 complete for R2.

**R3 — One new test needed** in `tests/test_auth.py`:

```python
@pytest.mark.django_db
def test_inactive_user_cannot_login(client: Client) -> None:
    user = User.objects.create_user(username="inactive", password="pass1234", is_active=False)
    response = client.post(
        "/accounts/login/",
        {"username": "inactive", "password": "pass1234"},
    )
    assert response.status_code == 200  # login page re-rendered, not redirected
    assert not response.wsgi_request.user.is_authenticated
```

This follows the established conventions:

- `@pytest.mark.django_db` (no `transaction=True` needed)
- No fixtures needed — user created inline (inactive user is test-specific, not shared state)
- `client.post()` with raw credentials (consistent with `test_auth.py:28-33`)
- Double assertion: status code + session authentication state

### Test file placement

`tests/test_auth.py` — this file already covers login/logout behavior. The inactive-user test is a direct extension of
that scope.

## Open Questions

1. **Should test_plan.md §5 be updated** to reflect that R2 is already covered (cross-user tests exist)? The current
   entry says "Not covered → Phase 2" but the tests do exist. Updating the coverage table as part of this change would
   keep the test-plan accurate.

2. **Generate endpoint returns 400 not 404/403** for cross-user ownership violations. The test-plan risk guidance says
   "returns 404, not 200 with changes applied." The existing tests assert 400, which is safe. Worth noting in plan
   whether the 400 status should stay as-is or be normalized to 404.
