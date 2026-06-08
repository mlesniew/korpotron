---
change_id: ui-refresh
title: Ui refresh
status: preparing
created: 2026-06-08
updated: 2026-06-08
archived_at: null
---

## Notes

<!-- Free-form notes for this change: links, ad-hoc context, decisions that don't belong in research/frame/plan. -->

## Decision (2026-06-08): Bootswatch — Zephyr theme

**Chosen approach:** Restyle by swapping the Bootstrap CDN stylesheet for the **Bootswatch
Zephyr** theme. Stay in the Bootstrap family for the lowest-effort, lowest-risk refresh.

**Why:** All templates already use Bootstrap classes and there is no build step. Bootswatch
is a 1:1 drop-in replacement for `bootstrap.min.css` — same class names, same DOM — so the
switch is essentially a one-line change with **zero template re-classing** and no new JS.
This matches the brief (SSR, no build, CDN-delivered static CSS, minimal JS) almost exactly.
See `research.md` for the full comparison; the runners-up were Tabler (more modern but needs
shell tweaks) and Bulma/Beer CSS/daisyUI (full re-class, rejected for effort/constraints).

**Concrete change:**
- Bootswatch 5.3.8, Zephyr theme.
- Replace the stylesheet `href` in `templates/base.html:7` **and** the duplicated link in
  `templates/core/landing.html:7`:
  ```html
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootswatch@5.3.8/dist/zephyr/bootstrap.min.css">
  ```
- Drop the existing Bootstrap `integrity`/SRI attribute on that link (the Bootswatch URL has
  a different hash), or compute Zephyr's own hash.
- No Bootstrap JS bundle is loaded today, so nothing changes on the JS side.

**Deliberately out of scope for this restyle (potential follow-ups):**
- Form styling: `{{ form.as_p }}` is unstyled under Bootstrap today and stays that way under
  Bootswatch (no regression). A later pass could add `crispy-bootstrap5`.
- Consolidating `landing.html` to extend `base.html` so the CDN URL lives in one place.
- Any custom-CSS tweaks (no `static/css` file exists yet).
