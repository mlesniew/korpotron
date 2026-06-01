# Follow-ups from implementation review (2026-05-29)

## Wire up mypy for Django models (django-stubs)

- **Source**: impl-review finding F2
- **Tracked in**: [mlesniew/korpotron#9](https://github.com/mlesniew/korpotron/issues/9)
- **Severity / Impact**: Observation / Low
- **Problem**: `uv run mypy .` reports 9 `var-annotated` errors, all in `core/models.py:6-44`
  (Template / OptionGroup / Option model fields). mypy cannot resolve Django field
  descriptors without django-stubs, so the type gate is effectively non-functional for
  models. This pre-dates the template-management change; the change's own files
  (`core/views.py`, `core/urls.py`, `tests/test_template_views.py`) are mypy-clean.
- **Why it matters**: CLAUDE.md states mypy is "to be wired into CI". As-is, wiring it
  would fail on these pre-existing model errors. The Phase 1 success criterion
  "Type checking passes: mypy . (if wired)" passed only by the "(if wired)" escape hatch.
- **Proposed fix**: `uv add --dev django-stubs[compatible-mypy]`, configure
  `mypy_django_plugin.main` + `django_settings_module = "korpotron.settings"` in the mypy
  config, confirm `uv run mypy .` is clean, then add it to CI.
- **Scope note**: Intentionally out of scope for template-management — it touches
  project-wide config and the shared models, not this feature.
