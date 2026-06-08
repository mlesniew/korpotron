# Option Group Edit UX (S-07) — Plan Brief

> Full plan: `context/changes/option-group-edit-ux/plan.md`

## What & Why

The option group edit page should show the editable group title plus all options at once, each with editable Name and Instructions fields and a Delete button that asks for browser confirmation, hides the row on confirm, and only removes the option from the database on form submit — all in one POST, no REST, vanilla JS. The goal is a clearer edit experience than a raw Django formset with DELETE checkboxes.

**Key fact:** this already shipped in commit `6122ab0` on `master`. The current template meets the full spec. This plan reconciles the tracking artifacts with that reality and closes the one real automated-coverage gap.

## Starting Point

`templates/core/optiongroup_form.html` already renders the editable title, all option rows with Name/Instructions, and a per-row Delete button wired to a vanilla-JS `confirm()` that toggles the formset's hidden `*-DELETE` input and hides the row. `OptionGroupUpdateView.form_valid` commits the form + formset in a single `transaction.atomic()` POST. Tests cover create/edit/group-delete/ownership/invariants — but not a server-side delete of an existing option. `change.md` is `new`, no plan exists, roadmap says `planned`, and GitHub issue #14 is open with stale "collapsible" wording.

## Desired End State

The edit page is confirmed and documented as meeting the spec (no template change). A new automated test proves a POST with an option's `DELETE` flag removes exactly that option while the group and other options survive. `change.md`, the roadmap (S-07 → done), and GitHub issue #14 (closed with a clarifying comment) all reflect reality. Full suite and lint stay green.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| How to treat already-shipped code | Reconcile + verify, don't rebuild | The template already meets the spec; rewriting risks regressing a passing feature. | Plan |
| Test coverage for delete | Add one server-side delete round-trip test | The JS only toggles the formset DELETE input; the persisted behavior is what needs locking in. | Plan |
| Browser-confirm / row-hide coverage | No E2E/browser test | No selenium/playwright infra exists; disproportionate for a Low-risk single-template change. | Plan |
| "Collapsible" wording in issue #14 | Close issue, keep non-collapsible design | Roadmap refined S-07 to "all options at once"; the shipped design is correct. | Roadmap |
| forms.py / views.py changes | None | Server-side single-POST delete path is already correct. | Plan |

## Scope

**In scope:**
- Verify and document the as-built template/formset behavior.
- Add an automated test for the existing-option delete round-trip.
- Update `change.md`, roadmap S-07 status, and close GitHub issue #14.

**Out of scope:**
- Rewriting or restyling the template; any REST/AJAX endpoint.
- Browser/E2E tests for the `confirm()` dialog.
- A collapsible option list; S-08/S-09 (dropped) and their issues #15/#16.

## Architecture / Approach

Django inline formset (`inlineformset_factory(..., can_delete=True)`) renders all option rows in one form. Vanilla JS replaces the raw DELETE checkbox with a Delete button: on confirm it checks the hidden `*-DELETE` input and hides the row. `OptionGroupUpdateView.form_valid` saves the parent form and the formset inside one `transaction.atomic()` block, so edits, deletes, and additions all commit on a single POST. The only code change this plan introduces is an additive test.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Verify & document as-built | Audited confirmation the shipped template meets the spec | Overlooking a spec clause — mitigated by clause-by-clause check |
| 2. Close test gap | Server-side delete round-trip test | Formset POST data shape (ids/INITIAL_FORMS) must be exact |
| 3. Reconcile artifacts | change.md, roadmap, issue #14 updated | Roadmap/issue wording drift — verified by grep + manual read |

**Prerequisites:** On branch `option-group-edit-ux`; clean tree; full suite green (58 passed) and lint clean at start.
**Estimated effort:** ~1 short session across 3 phases (mostly verification + one test + artifact edits).

## Open Risks & Assumptions

- Assumes the user wants the plan to reflect the already-shipped reality rather than rebuild the feature; rebuilding would be wasteful and risky (AskUserQuestion was unavailable in this background run, so this was decided from codebase evidence).
- The delete round-trip test must supply correct formset management data (`INITIAL_FORMS`, `options-N-id`) and keep ≥1 surviving option to avoid tripping the required-option validator.
- Issue #14's "collapsible" framing is treated as superseded by the roadmap's refined outcome.

## Success Criteria (Summary)

- The edit page shows the editable title and all options, each with Name/Instructions and a Delete button that confirms, hides on confirm, and deletes from the DB only on Save.
- An automated test guarantees the existing-option delete round-trip; full suite and lint stay green.
- `change.md`, roadmap (S-07 → done), and GitHub issue #14 all reflect the shipped state.
