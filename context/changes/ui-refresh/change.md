---
change_id: ui-refresh
title: Ui refresh
status: implementing
created: 2026-06-08
updated: 2026-06-09
archived_at: null
---

## Notes

<!-- Free-form notes for this change: links, ad-hoc context, decisions that don't belong in research/frame/plan. -->

## Decision (2026-06-08): Implement the `design_handoff/` redesign (raw Bootstrap + custom CSS)

**Chosen approach:** Recreate the high-fidelity designs in
`context/changes/ui-refresh/design_handoff/` as the project's Django templates. The design
**keeps raw Bootstrap 5** (grid + utilities, loaded from the CDN as today) and layers a custom
design system on top via a new `static/css/korpotron.css`. This replaces the framework swap
that was previously under consideration.

> **Supersedes the earlier Bootswatch/Zephyr decision.** A custom, purpose-built design now
> exists, so a generic theme is no longer needed. The framework comparison in `research.md`
> remains as historical context, but its Bootswatch recommendation is no longer the plan —
> we stay on raw Bootstrap and add bespoke styling instead.

### What the handoff provides

A `README.md` plus six high-fidelity HTML prototypes (one per screen). They are **design
references, not production code** — recreate them as Django templates wired to real template
tags, form rendering, URL reversals, CSRF, and the existing formset/generate JS. Do **not**
copy the prototype HTML (it uses dummy data and prototype-only JS).

### Design system (from `design_handoff/README.md`)

- **`static/css/korpotron.css`** (new file): oklch colour tokens, radii, shadows; loaded
  from `base.html` **after** Bootstrap, overriding Bootstrap variables where they conflict.
- **Typography:** IBM Plex Sans (body) + IBM Plex Mono (brand name, Generate button) via
  Google Fonts `<link>` in `base.html`.
- **Custom components** beyond Bootstrap: pill buttons, CSS-only toggle switch, custom delete
  dialog, output card, frosted-glass sticky nav.

### Screens to rebuild (handoff file → Django template)

| Handoff file | Django template |
|---|---|
| `Korpotron Landing.html` | `templates/core/landing.html` (login now an **embedded modal**) |
| `Korpotron Generate.html` | `templates/core/generate.html` |
| `Korpotron Templates.html` | `templates/core/template_list.html` |
| `Korpotron Template Form.html` | `templates/core/template_form.html` |
| `Korpotron Modifiers.html` | `templates/core/optiongroup_list.html` |
| `Korpotron Modifier Form.html` | `templates/core/optiongroup_form.html` |

### Notable scope points

- **Login** moves into a modal overlay on the landing page. Keep a minimal styled standalone
  `templates/registration/login.html` (matching the modal) for `@login_required` redirects.
- **"Option Groups" → "Modifiers"** is a **display-label rename only** — Django URL names and
  models (`OptionGroup`, `option-group-*`) stay unchanged.
- **Forms** are now bespoke per the designs (toggle switch, pill rows, two-column option
  formset), so `{{ form.as_p }}` is replaced by hand-built markup — no crispy-forms needed.
- Custom JS stays vanilla: keep the existing formset add/delete pattern (restyled), generate
  fetch flow (with rotating "loading quips"), clipboard copy, and the delete dialog.
- `oklch()` is fine for all modern browsers (hex fallbacks available in the token table).
