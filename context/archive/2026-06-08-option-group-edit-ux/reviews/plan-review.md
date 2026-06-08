<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Option Group Edit UX (S-07) Reconciliation

- **Plan**: context/changes/option-group-edit-ux/plan.md
- **Mode**: Deep
- **Date**: 2026-06-08
- **Verdict**: REVISE (light — all fixes are LOW impact; none blocks implementation)
- **Findings**: 0 critical, 3 warnings, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | WARNING |
| Plan Completeness | WARNING |

## Grounding

6/6 paths exist; symbols confirmed (`can_delete=True` forms.py:31, `form_valid` views.py:113-120, `delete-option` template.html:35/52/66, `RequiredOptionInlineFormSet` forms.py:10); brief↔plan consistent; baseline reproduced (`uv run pytest -q` → 58 passed, `ruff check .` clean); commit `6122ab0` confirmed on branch `option-group-edit-ux`; GitHub issue #14 confirmed OPEN with stale "collapsible" title. The "already shipped" premise is fully verified — the template, formset, and view match every clause of the plan's as-built claims.

## Findings

### F1 — New delete test needs formset id/management data the helper doesn't emit

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 2 — Delete-on-submit test
- **Detail**: The shared `formset_data()` helper (tests/test_option_group_views.py:22-34) hardcodes `INITIAL_FORMS: "0"` and emits no `options-N-id` field. Deleting an *existing* (saved) option requires `INITIAL_FORMS` = number of saved rows and an `options-N-id` per row. The only existing test that deletes (`test_option_group_create_requires_at_least_one_option`, line 137) deletes an UNSAVED row, so this path was never exercised. The plan flags "include options-N-id and correct INITIAL_FORMS" in prose but provides no helper for it; the implementer must build the POST dict inline (as `test_option_group_update` does, lines 78-88) with TWO option rows. If they reach for `formset_data()` by habit, the test silently won't delete a persisted row and would pass vacuously.
- **Fix**: In Phase 2 Contract, state explicitly: build POST data inline (mirroring `test_option_group_update` lines 78-88), set `options-INITIAL_FORMS=2`, include `options-0-id` and `options-1-id`, mark one row `DELETE=on`, keep the other intact. (Manual criterion 2.5 — "test fails when can_delete removed" — partially guards against a vacuous test, but does not catch the unsaved-row trap.)
- **Decision**: PENDING

### F2 — lessons.md "verify Docker build before commit" not addressed

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 2 / Testing Strategy
- **Detail**: lessons.md records an accepted rule (Applies to: plan, implement): "After finishing implementation and before committing changes, check if docker build succeeds." A Dockerfile exists at repo root. Phase 2 commits a code change (the new test) but no phase mentions a Docker build check. The change is test-only Python and very unlikely to break the build, but the lesson is a standing prior the plan-review weighs as a prior — the plan should either honor it or explicitly waive it with a reason.
- **Fix**: Add a one-line note to Phase 2 verification: run (or explicitly waive with reason) `docker build .` before commit, per lessons.md. A test-only change is a reasonable waiver — just state it so the lesson is consciously discharged.
- **Decision**: PENDING

### F3 — Roadmap has two S-07 status tables; Phase 3 grep is ambiguous

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 3 #2 (roadmap) + verification line 155
- **Detail**: roadmap.md carries the S-07 `planned` status in TWO tables — the "At a glance" table (line 40) AND a second status table (line 252) — plus a Stream D narrative (line 57) and a closing summary line (240) reading "S-07, S-10, and S-11 remain planned." Phase 3 says update "the At a glance table (and any S-07 detail block / Stream D note)" but its grep verification `grep -n "option-group-edit-ux" ... shows done` matches lines 40 and 252 only; line 240 uses bare "S-07" (not the change-id) and won't be caught. Risk: one of the four locations is left stale and the roadmap reads incoherently.
- **Fix**: Phase 3 #2 Contract should enumerate all four spots: At-a-glance table (40), second status table (252), Stream D note (57), summary paragraph (240). Strengthen verification to assert no remaining "S-07 ... planned" in the status tables.
- **Decision**: PENDING

### F4 — Phase 1 grep under-covers its own "raw checkbox suppressed" claim

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 Automated Verification (line 73)
- **Detail**: The criterion reads "Delete button present and raw checkbox suppressed: `grep -q 'delete-option'`". The grep proves only the button exists. The "suppressed checkbox" half is implemented via `<div style="display:none">{{ option_form.DELETE }}</div>` (template line 21) — the DELETE field is still rendered (correctly, since the JS toggles it), just visually hidden. So "suppressed" is a slight mischaracterization and the grep tests neither the hiding nor the field. Cosmetic only — the feature is correct.
- **Fix**: Either drop "and raw checkbox suppressed" from the criterion, or add a second grep asserting the `display:none` wrapper around `option_form.DELETE`.
- **Decision**: PENDING
