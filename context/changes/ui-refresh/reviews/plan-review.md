<!-- PLAN-REVIEW-REPORT -->
# Plan Review: UI Refresh Implementation Plan

- **Plan**: context/changes/ui-refresh/plan.md
- **Mode**: Deep
- **Date**: 2026-06-08
- **Verdict**: REVISE
- **Findings**: 1 critical  1 warning  1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | WARNING |
| Plan Completeness | FAIL |

## Grounding

14/14 paths ✓ (static/ and new files correctly absent), 6/6 symbols ✓, brief↔plan ✓

## Findings

### F1 — Existing delete tests assert 302 — will fail when views return 204

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 3 — DeleteViews return 204 / Testing Strategy
- **Detail**: Two existing tests will fail the moment the view change lands: `tests/test_template_views.py:67-68` asserts `status_code == 302` and `response["Location"] == "/templates/"`, and `tests/test_option_group_views.py:106-107` asserts `status_code == 302` and `response["Location"] == "/option-groups/"`. Phase 3 Success Criteria say "Existing + new tests pass" — impossible without updating these assertions. The Testing Strategy says "add a new 204 test" and "keep test_core_models.py green", silently skipping the tests that will fail.
- **Fix**: In Phase 3, item 1 (DeleteViews return 204), add an explicit step: "Update `tests/test_template_views.py` lines 67-68 and `tests/test_option_group_views.py` lines 106-107 — change assert `status_code == 302` to `== 204` and remove the Location assertions."
- **Decision**: PENDING

### F2 — GET /delete/ returns 500 after confirm-template removal

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 3 — items 1 and 2
- **Detail**: Phase 3 removes confirm-delete templates (item 2) but doesn't restrict both DeleteViews to POST-only. Django's `DeleteView` serves GET to render the confirmation template. After removal, any GET to `/templates/<pk>/delete/` or `/option-groups/<pk>/delete/` raises `TemplateDoesNotExist` → 500. The current list templates have `<a href>` links to these URLs (`template_list.html:23`, `optiongroup_list.html:25`) — these are replaced in Phase 3 items 4–5, but an implementer who does items 1+2 before 4+5 will see 500s.
- **Fix**: Add `http_method_names = ['post']` to both `TemplateDeleteView` and `OptionGroupDeleteView` in Phase 3 item 1, alongside the 204 change. This makes GET return 405 (not 500). A 2-line addition.
- **Decision**: PENDING

### F3 — Docker build missing from phase Success Criteria

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Migration Notes / Phase 4 Success Criteria
- **Detail**: `lessons.md` mandates "check if docker build succeeds" before committing. The plan acknowledges this in Migration Notes prose ("verify the Docker build before merging") but it's absent from every phase's Success Criteria checklist. An implementer working through the checklist will miss it.
- **Fix**: Add `docker build .` as a step in Phase 4 Automated Success Criteria (final phase, just before merge-ready).
- **Decision**: PENDING
