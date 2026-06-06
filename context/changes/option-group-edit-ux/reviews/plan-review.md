<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Option Group Edit UX — full AJAX redesign

- **Plan**: context/changes/option-group-edit-ux/plan.md
- **Mode**: Deep
- **Date**: 2026-06-06
- **Verdict**: REVISE
- **Findings**: 0 critical, 4 warnings, 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | WARNING |
| Blind Spots | WARNING |
| Plan Completeness | WARNING |

## Grounding

6/6 paths ✓, 5/5 symbols ✓, brief↔plan ✓.
- CSRF cookie ✓ — `base.html:17` `{% csrf_token %}` renders under `is_authenticated`; the edit page is login-required, so the `csrftoken` cookie is always set. Matches existing `generate.html` `getCookie('csrftoken')` pattern. No finding.
- Formset blast radius ✓ — every `OptionFormSet` / `formset` reference is contained in the four touched files (forms.py, views.py, optiongroup_form.html, test_option_group_views.py). No external callers.
- Progress↔Phase ✓ — exactly one `## Progress` heading, all three phase headings match, no checkboxes in phase blocks. Progress granularity is coarser than the Success Criteria bullets (Phase 1: 5 manual criteria → 1.3/1.4; Phase 2: 9 → 2.2/2.3/2.4), but `/10x-implement` walks `- [ ]` lines and parses it fine — not a blocker.

## Findings

### F1 — option_create contract will throw IntegrityError as written

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Completeness
- **Location**: Phase 1, §7 (option_create), line 159
- **Detail**: `OptionForm` is defined with `fields = ["name", "instruction"]` (§1, line 94) — no `group` field. `Option.group` is a non-nullable FK (models.py:39-43). The contract says "validate with OptionForm(data=payload) ... create option" without assigning the group. A literal `form.save()` inserts with group_id = NULL → IntegrityError → 500. An implementer following the contract verbatim hits this on the first create.
- **Fix**: Specify the save pattern explicitly in §7: `option = form.save(commit=False); option.group = group; option.save()`. §8 (update) uses `instance=option` so group is already bound — no change there, but call it out to avoid copy-paste error.
- **Decision**: PENDING

### F2 — Duplicate-name 400 has no defined response shape; JS can't display it

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Completeness
- **Location**: Phase 1 §7/§8; Phase 2 §11 (Save handlers, lines 260-261)
- **Detail**: Form-validation failures return `{"errors": form.errors}` — a field-keyed dict the JS "show field errors" handler expects (`.option-name-error`, etc.). But the duplicate-name check is a separate `group.options.filter(name=...).exists()` branch whose response shape is never stated. Rename (§6) returns flat `{"error": "..."}`. If create/update reuse the flat shape, the duplicate error won't render under the name field — the most common user error becomes invisible.
- **Fix**: Mandate the duplicate branch return field-keyed errors matching form.errors, e.g. `{"errors": {"name": ["An option with this name already exists."]}}`, status 400. The existing field-error renderer then handles it with no special-casing.
- **Decision**: PENDING

### F3 — New endpoints omit the defensive JSON parsing the cited pattern relies on

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 1 §6/§7/§8 ("Parse JSON body")
- **Detail**: The plan says endpoints "follow the generate_api pattern," but generate_api's robustness lives in code the per-endpoint contracts drop: `try: json.loads(request.body) except (JSONDecodeError, UnicodeDecodeError)` + `isinstance(payload, dict)` guards (views.py:156-161). The contracts just say "Parse JSON body." A literal `payload = json.loads(request.body)` 500s on a malformed/non-JSON body. Three mutation endpoints share this gap.
- **Fix**: State in each contract that JSON parsing must reuse the generate_api guard (try/except + isinstance-dict → 400 "Invalid request."). Consider a small shared helper since the block now repeats four times.
- **Decision**: PENDING

### F4 — "Two separate URLs at the same path" alternative is broken in Django

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Architectural Fitness
- **Location**: Phase 1 §10, line 197
- **Detail**: §10 offers (a) a single dispatcher view or (b) "two separate named URLs pointing to separate views." Option (b) does not work — Django resolves URLs by path only; two `path()` entries with the identical route mean the first always wins for every method, so the POST view is unreachable. Also §5/§7 decorate `option_list` (GET) and `option_create` (@require_POST) separately; merged into one dispatcher, `@require_POST` can't wrap the whole view. The plan recommends the dispatcher, but the alternative is a trap and the decorator split is muddled.
- **Fix**: Drop option (b). Specify a single `option_list_create` view, `@login_required` only, branching on `request.method` (GET → list, POST → create, else `HttpResponseNotAllowed(["GET", "POST"])`). One URL name `"option-list-create"`.
- **Decision**: PENDING

### F5 — Option list ordering is unspecified

- **Severity**: 🔭 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 1 §5 (option_list), line 131
- **Detail**: `Option.Meta` has no `ordering` (models.py:47-48 — only unique_together). `group.options.all()` returns DB-default order, so newly created options can appear in inconsistent positions across reloads. OptionGroup/Template both define `ordering`; Option is the odd one out.
- **Fix**: Add `.order_by("name")` (or "pk") in option_list. Prefer the view-level order over an Option.Meta change to honor the plan's "no model changes required" invariant (line 41).
- **Decision**: PENDING

### F6 — Empty-warning "shown while loading" contradicts the hidden-initial decision

- **Severity**: 🔭 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: End-State Alignment
- **Location**: Plan line 74 vs Phase 2 manual criteria, line 275
- **Detail**: The decision (line 74) says the warning starts hidden (`d-none`) and `updateEmptyWarning()` runs only after the first fetch. But Phase 2 manual verification (line 275) asserts it is "shown while options are loading." With the hidden-initial approach it is NOT shown during load — only after fetch resolves to zero options. The verification step as written would "fail" a correct implementation.
- **Fix**: Reword line 275 to "hidden during load; shown only after fetch resolves with zero options."
- **Decision**: PENDING
