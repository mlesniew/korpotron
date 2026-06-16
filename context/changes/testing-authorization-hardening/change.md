---
change_id: testing-authorization-hardening
title: Authorization hardening — ownership isolation tests for JSON endpoints and inactive-user login block
status: implementing
created: 2026-06-16
updated: 2026-06-16
archived_at: null
---

## Notes

Rollout Phase 2 of context/foundation/test-plan.md.

Risks covered: R2 (IDOR on JSON endpoints — cross-user ownership bypass), R3 (inactive-user login bypass on S-11
registration flow). Test types planned: Django test client integration tests.

Risk response intent:

- R2: prove that a cross-user POST/PATCH/DELETE to a JSON endpoint returns 403/404, not 200 with changes applied;
  challenge the assumption that login_required implies ownership; avoid testing only the own-user happy path.
- R3: prove that a user registered via S-11 with is_active=False cannot log in before admin approval; challenge the
  assumption that Django blocks inactive users automatically for the configured auth backend; avoid asserting only that
  the registration form saves data without verifying login is blocked.
