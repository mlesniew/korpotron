# Option Group Edit UX (S-07) Implementation Plan

## Overview

Improve the option group edit page so it shows the group title (editable) plus every option at once, each with editable Name and Instructions fields and a Delete button. Clicking Delete shows a browser `confirm()` dialog; on confirm the row is hidden and tagged for removal, with the actual database delete happening only when the form is submitted. All edits, deletes, and additions commit in a single form POST through the existing Django inline formset — no REST endpoints, vanilla JS only.

**Important context discovered during research:** the substance of this change already landed on `master` in commit `6122ab0` ("feat(option-group-edit-ux): replace DELETE checkbox with JS delete-with-confirm button"). `templates/core/optiongroup_form.html` already satisfies every line of the S-07 outcome. This plan is therefore a **reconciliation + verification** plan, not a build-from-scratch plan: it documents the as-built state, closes the one genuine automated-coverage gap (a server-side test proving the formset delete round-trips), and brings the tracking artifacts (`change.md`, roadmap, GitHub issue) in line with reality. Rewriting the working template is explicitly out of scope — it would be wasteful and risk regressing a passing feature.

## Current State Analysis

- `templates/core/optiongroup_form.html` (HEAD) already renders:
  - The editable group title via `{{ form.as_p }}` (line 8).
  - Every option as a `.option-row` with explicit `Name` and `Instructions` labels/fields and per-field error blocks (lines 18–37).
  - A visible `Delete` button per row (line 35), and an `Add option` button (line 56) that clones an `<template id="empty-option-row">` and renumbers `__prefix__`.
  - Vanilla JS (lines 64–95): `wireDeleteButton` attaches a click handler that calls `confirm('Delete this option?')`, and on confirm sets the hidden `*-DELETE` checkbox to checked and hides the row via `style.display='none'`. New rows get the same wiring on add.
- `core/forms.py` defines `OptionFormSet` via `inlineformset_factory(OptionGroup, Option, ..., can_delete=True, extra=1)` with a `RequiredOptionInlineFormSet` that enforces ≥1 surviving option and unique option names within the group.
- `core/views.py` `OptionGroupUpdateView.form_valid` (lines 113–120) saves the form and formset inside a single `transaction.atomic()` on one POST — deletes, edits, and new options all commit together. `OptionGroupCreateView` mirrors this.
- `tests/test_option_group_views.py` covers create, update (edit of an option's instruction), group delete, ownership 404s, the ≥1-option rule, and the duplicate-name rule. **Gap:** no test posts `DELETE=on` for an *existing* option and asserts that option is removed from the DB while the group and its other data survive — i.e. the exact server-side path the new Delete button drives.
- Full suite is green (58 passed) and `ruff check .` is clean at the start of this plan.
- `change.md` status is `new`. No `plan.md`/`plan-brief.md` exist yet. Roadmap marks S-07 `planned`. GitHub issue `#14` is OPEN and titled "collapsible inline option list" — stale framing (S-07 was refined to a non-collapsible "all options at once" design) and stale status.

## Desired End State

- `optiongroup_form.html` is confirmed (and documented) to meet the S-07 spec; no behavioral change to the template is required.
- A new automated test proves that a single edit-view POST with an option's `DELETE` field set removes that option from the database while leaving the group and any non-deleted options intact. Run `uv run pytest tests/test_option_group_views.py -q` → all pass.
- `change.md` reflects the true lifecycle state, roadmap S-07 is marked `done`, and GitHub issue `#14` is closed with a comment reconciling the refined (non-collapsible) outcome.
- Full suite green, `ruff check .` and `ruff format --check .` clean.

### Key Discoveries:

- Implementation already shipped: `templates/core/optiongroup_form.html:35,64-77` (Delete button + JS confirm + DELETE-checkbox wiring), commit `6122ab0`.
- Single-POST commit path: `core/views.py:113-120` (`form.save()` + `formset.save()` inside one `transaction.atomic()`).
- Delete capability comes from the formset factory: `core/forms.py:31` (`can_delete=True`); the JS only toggles the formset's own hidden `*-DELETE` input.
- ≥1-option and unique-name invariants live in `RequiredOptionInlineFormSet.clean` (`core/forms.py:11-22`) and already account for `DELETE`ed rows.
- No browser/E2E test harness exists in the repo (no selenium/playwright) — the `confirm()`/row-hide UI is intentionally not covered by an automated browser test for this Low-risk single-template change.
- GitHub issue `#14` title ("collapsible inline option list") predates the roadmap refinement to the current "all options at once" spec — close with a clarifying comment rather than re-implementing a collapsible UI.

## What We're NOT Doing

- Not rewriting or restyling `optiongroup_form.html` — it already meets the spec.
- Not adding a Selenium/Playwright/browser-driven test for the `confirm()` dialog or row-hide behavior; no E2E infra exists and it is disproportionate for a Low-risk JS-only change.
- Not building any REST/AJAX endpoint — deletes stay in the single form POST.
- Not implementing a "collapsible" option list (the original issue #14 wording); the refined S-07 outcome is "all options at once".
- Not touching S-08 / S-09 (dropped slices) or their open issues #15/#16 beyond noting they remain open and out of scope.
- Not modifying `core/forms.py` or `core/views.py` — the server-side behavior is already correct.

## Implementation Approach

Treat the change as already-implemented and drive it to a verified, reconciled close. Phase 1 verifies and documents the as-built behavior against the spec (read-only). Phase 2 adds the single missing automated test that locks in the server-side delete round-trip the new button depends on. Phase 3 reconciles tracking artifacts (`change.md`, roadmap, GitHub issue). Each phase is independently safe; the only code change is additive test code.

## Phase 1: Verify & Document As-Built State

### Overview

Confirm the shipped template and formset wiring satisfy every clause of the S-07 outcome, with no code changes. This phase is the auditable record that the feature is present and correct.

### Changes Required:

#### 1. As-built verification (no file changes)

**File**: `templates/core/optiongroup_form.html` (read-only review), `core/forms.py`, `core/views.py`

**Intent**: Walk each S-07 clause (editable title; all options shown; per-row editable Name/Instructions; per-row Delete with browser confirm; hidden-until-submit deletion; single POST; no REST; vanilla JS) and confirm a corresponding implementation point. Record the mapping in the implementation notes / commit message; do not alter code.

**Contract**: No code delta. The invariant to assert: deletion is driven solely by the formset's hidden `*-DELETE` input toggled by `wireDeleteButton`, and persistence happens only in `OptionGroupUpdateView.form_valid`'s `transaction.atomic()` block.

### Success Criteria:

#### Automated Verification:

- Existing option group tests pass: `uv run pytest tests/test_option_group_views.py -q`
- Lint clean: `uv run ruff check .`
- Delete button present and raw checkbox suppressed: `grep -q "delete-option" templates/core/optiongroup_form.html`

#### Manual Verification:

- On the edit page, the group title and all options render at once, each with editable Name and Instructions.
- Clicking Delete shows a browser confirmation; cancelling leaves the row; confirming hides it.
- A hidden (deleted) option only disappears from the database after Save is clicked; navigating away without saving preserves it.
- Adding an option via "Add option" produces a fully wired row (including a working Delete button).

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Close the Delete Round-Trip Test Gap

### Overview

Add one automated test asserting that an edit-view POST carrying an existing option's `DELETE` flag removes that option from the database (group and non-deleted options survive). This locks in the exact server-side behavior the Delete button triggers.

### Changes Required:

#### 1. Delete-on-submit test

**File**: `tests/test_option_group_views.py`

**Intent**: Add a `@pytest.mark.django_db` test that, for a group with two options, POSTs the edit view with one option marked `DELETE=on` and the other left intact, then asserts the deleted option is gone, the surviving option remains, and the group still exists. Reuse the existing `formset_data`/inline-data style already in the file (include `options-N-id` for initial rows and correct `INITIAL_FORMS`).

**Contract**: New test function in `tests/test_option_group_views.py`. Posts to `/option-groups/<pk>/edit/`; expects 302 to `/option-groups/`; `Option.objects.filter(pk=deleted_pk).exists()` is `False`, the surviving option still exists, and `OptionGroup.objects.filter(pk=group_pk).exists()` is `True`. The group fixture must carry two options (extend locally or build inline) so deleting one does not trip the ≥1-option rule.

### Success Criteria:

#### Automated Verification:

- New test passes: `uv run pytest tests/test_option_group_views.py -q`
- Full suite passes: `uv run pytest -q`
- Lint clean: `uv run ruff check .`
- Format clean: `uv run ruff format --check .`

#### Manual Verification:

- The new test fails if `can_delete=True` is removed from the formset factory (sanity-check it actually exercises the delete path).

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Reconcile Tracking Artifacts

### Overview

Bring the change-tracking artifacts in line with the delivered reality: change identity file, roadmap status, and the GitHub issue.

### Changes Required:

#### 1. Change identity file

**File**: `context/changes/option-group-edit-ux/change.md`

**Intent**: Set `status` to `done` and `updated` to today, reflecting that the implementation and verification are complete. (The `/10x-plan` step itself sets `planned`; this phase advances it to `done` once Phases 1–2 land.)

**Contract**: YAML frontmatter `status` and `updated` fields.

#### 2. Roadmap status

**File**: `context/foundation/roadmap.md`

**Intent**: Update the S-07 row in the "At a glance" table (and any S-07 detail block / Stream D note) from `planned` to `done`.

**Contract**: The S-07 status cell reads `done`; Stream D narrative consistent.

#### 3. GitHub issue reconciliation

**File**: GitHub issue `#14` (via `gh`)

**Intent**: Comment on issue `#14` clarifying that S-07 shipped as a non-collapsible "all options at once" edit page with a JS delete-with-confirm button (refined away from the original "collapsible inline option list" wording), referencing commit `6122ab0`, then close it. Per `lessons.md` ("Sync GitHub issues with context changes").

**Contract**: Issue `#14` closed with an explanatory comment. (Issues #15/#16 for dropped S-08/S-09 are out of scope here.)

### Success Criteria:

#### Automated Verification:

- Roadmap S-07 marked done: `grep -n "option-group-edit-ux" context/foundation/roadmap.md` shows `done`.
- Change file updated: `grep -n "status:" context/changes/option-group-edit-ux/change.md` shows `done`.
- Issue closed: `gh issue view 14 --json state -q .state` returns `CLOSED`.

#### Manual Verification:

- Roadmap reads coherently (Stream D note and S-07 row agree).
- Issue #14's closing comment accurately reflects the shipped, non-collapsible behavior.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the reconciliation reads correctly.

---

## Testing Strategy

### Unit Tests:

- New: edit-view POST with one option's `DELETE` set removes exactly that option; group and other options survive (Phase 2).
- Existing (regression): create, update/edit-instruction, group delete, ownership 404s, ≥1-option rule, duplicate-name rule.

### Integration Tests:

- The delete round-trip test is itself an integration test through the view + formset + ORM (Django test client POST to the real URL).

### Manual Testing Steps:

1. Open an existing option group's edit page; confirm title + all options render with editable fields.
2. Click Delete on an option; cancel the confirm — row stays. Click Delete again; confirm — row hides.
3. Click Save; reopen the group — the deleted option is gone, others persist.
4. Repeat the delete but navigate away before Save — the option is still present (delete is submit-bound).
5. Click "Add option", fill it, Save — the new option persists and its Delete button works.

## Performance Considerations

None. Single-form POST over a small option set; no new queries beyond the existing formset save.

## Migration Notes

None. No model or schema changes.

## References

- Shipped implementation: commit `6122ab0`; `templates/core/optiongroup_form.html:35,56,64-95`
- Single-POST commit path: `core/views.py:113-120`
- Formset + invariants: `core/forms.py:10-32`
- Existing tests: `tests/test_option_group_views.py`
- Roadmap slice: `context/foundation/roadmap.md` (S-07, Stream D)
- Lessons: `context/foundation/lessons.md` (verify Docker build before commit; sync GitHub issues)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Verify & Document As-Built State

#### Automated

- [x] 1.1 Existing option group tests pass — 520dc2e
- [x] 1.2 Lint clean — 520dc2e
- [x] 1.3 Delete button present and raw checkbox suppressed (grep) — 520dc2e

#### Manual

- [ ] 1.4 Title + all options render with editable fields
- [ ] 1.5 Delete shows confirm; cancel keeps row, confirm hides it
- [ ] 1.6 Deleted option removed from DB only after Save
- [ ] 1.7 Added option row is fully wired (incl. Delete)

### Phase 2: Close the Delete Round-Trip Test Gap

#### Automated

- [x] 2.1 New delete-on-submit test passes — 2c98572
- [x] 2.2 Full suite passes — 2c98572
- [x] 2.3 Lint clean — 2c98572
- [x] 2.4 Format check clean — 2c98572

#### Manual

- [x] 2.5 Test fails when `can_delete=True` is removed (exercises delete path) — 2c98572

### Phase 3: Reconcile Tracking Artifacts

#### Automated

- [x] 3.1 Roadmap S-07 marked done (grep)
- [x] 3.2 change.md status done (grep)
- [x] 3.3 GitHub issue #14 CLOSED

#### Manual

- [ ] 3.4 Roadmap reads coherently (Stream D + S-07 row agree)
- [ ] 3.5 Issue #14 closing comment reflects shipped behavior
