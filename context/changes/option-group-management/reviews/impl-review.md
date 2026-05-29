<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Option Group Management

- **Plan**: context/changes/option-group-management/plan.md
- **Scope**: All 3 Phases
- **Date**: 2026-05-29
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 2 warnings, 5 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Automated Criteria Results

| Check | Result |
|-------|--------|
| `uv run manage.py migrate --check` | ✅ PASS |
| `uv run manage.py check` | ✅ PASS |
| `uv run pytest` (26 tests) | ✅ PASS |
| `uv run ruff check .` | ✅ PASS |
| `docker build .` | ✅ PASS |

## Findings

### F1 — N+1 COUNT query in option group list

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: templates/core/optiongroup_list.html:22
- **Detail**: `{{ group.options.count }}` is called inside a `{% for group in object_list %}` loop. Django issues one `COUNT(*)` SQL query per group row, producing N+1 queries total. The sibling `template_list.html` has no sub-count column so this pattern is genuinely new here.
- **Fix**: Annotate the queryset in `OptionGroupListView.get_queryset()` with `.annotate(options_count=Count("options"))` and use `{{ group.options_count }}` in the template.
  - Strength: One queryset annotation collapses N extra queries into the initial SELECT — a standard Django pattern.
  - Tradeoff: Minor — two lines in the view, one token change in the template, plus importing `Count` from `django.db.models`.
  - Confidence: HIGH — identical pattern is the textbook fix for this class of N+1 in Django list views.
  - Blind spot: None significant.
- **Decision**: FIXED — annotated queryset with Count("options") in OptionGroupListView; template updated to use options_count.

### F2 — Formset double-construction on invalid POST (Create + Update)

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Pattern Consistency
- **Location**: core/views.py:61–74 (Create), 85–99 (Update)
- **Detail**: `get_context_data` constructs a fresh `OptionFormSet(request.POST or None)` on every call. `form_valid` then constructs a second formset to validate. When the formset is invalid, the error re-render path calls `get_context_data` again — a third construction from the same POST data. The displayed errors are still correct (same POST), but the validated formset object is discarded and a new one is shown to the user. This is fragile: any state on the formset object (custom error annotations, cross-field clean results) would be lost on re-render. The plan described this arrangement, so it is not drift — but it is the standard Django CBV anti-pattern for inline formsets.
- **Fix A ⭐ Recommended**: Cache the validated formset on `self` in `form_valid` and in `form_invalid`, then return it from `get_context_data` if already set (i.e., `if hasattr(self, "_formset"): return self._formset` instead of constructing a new one).
  - Strength: Eliminates redundant construction without changing external behaviour; formset errors are always from the validated instance.
  - Tradeoff: Slightly more code in `get_context_data`; instance state must be cleared between requests (fine — CBVs are per-request).
  - Confidence: HIGH — this is the recommended Django pattern for CBVs with inline formsets.
  - Blind spot: Need to verify UpdateView's `form_invalid` path also passes through correctly.
- **Fix B**: Accept as-is and add a code comment explaining the pattern.
  - Strength: Zero code change; the behavior is already correct.
  - Tradeoff: Fragility remains; future contributors may be confused by why the formset is constructed in two places.
  - Confidence: MEDIUM — acceptable if the views are not expected to gain complexity.
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A — cached formset on self._formset in both CreateView and UpdateView.

### F3 — other_user fixture duplicated across test modules

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/test_option_group_views.py:8–10 (also tests/test_template_views.py:8–10)
- **Detail**: `other_user` is defined identically in both test modules. The `user` fixture lives in `conftest.py`; `other_user` should too.
- **Fix**: Move `other_user` to `tests/conftest.py` and delete both local definitions.
- **Decision**: FIXED — moved other_user to tests/conftest.py and removed both local definitions.

### F4 — Delete confirm template: `<strong>` vs plan's typographic quotes

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: templates/core/optiongroup_confirm_delete.html:5
- **Detail**: Plan specified `Delete "{{ object.name }}"? …`. Implementation uses `Delete <strong>{{ object.name }}</strong>? …`. Using `<strong>` is arguably better UX than literal quotes, but it is a departure from the plan. The sibling `template_confirm_delete.html` uses quotes, not `<strong>`.
- **Fix**: Either align with `template_confirm_delete.html` and use quotes, or update the sibling template to also use `<strong>` for consistency.
- **Decision**: DISMISSED — both delete templates already use `<strong>` consistently; the finding's claim about the sibling using quotes was incorrect.

### F5 — BaseInlineFormSet unparameterized (future mypy concern)

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: core/forms.py:6
- **Detail**: `RequiredOptionInlineFormSet(BaseInlineFormSet)` — `BaseInlineFormSet` is not type-parameterized. Under strict mypy this will produce a "Missing type parameters" warning. mypy is not yet wired into CI (a known follow-up item), so this is dormant for now.
- **Fix**: Defer until mypy is added to CI; address alongside other Django stubs typing work.
- **Decision**: FIXED — added django_stubs_ext.monkeypatch() to settings.py; parameterized RequiredOptionInlineFormSet with BaseInlineFormSet[Option, OptionGroup, ModelForm[Option]].

### F6 — No unique_together (user, name) on OptionGroup

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: core/models.py:22–34
- **Detail**: A user can create two OptionGroups with the same name. The `Template` model has the same omission, so this is consistent — but it may be a silent UX footgun. Not a code defect, a domain design question.
- **Fix**: Add `unique_together = [("user", "name")]` to `OptionGroup.Meta` and generate a migration if uniqueness per-user is a business requirement.
- **Decision**: FIXED — added unique_together = [("user", "name")] to OptionGroup.Meta; generated migration 0003.

### F7 — core/option_group_urls.py is a separate file vs core/urls.py pattern

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: core/option_group_urls.py
- **Detail**: Template URLs live in `core/urls.py`; option-group URLs live in a new separate file. The plan justified this to avoid restructuring the existing URL file, which is reasonable. But `core` now has two URL modules, making discovery less intuitive.
- **Fix**: Either consolidate both into `core/urls.py`, or accept the split as the project's going-forward pattern (one URL file per feature module).
- **Decision**: FIXED — consolidated both URL modules into core/urls.py with full path prefixes; korpotron/urls.py now has a single include; deleted option_group_urls.py.
