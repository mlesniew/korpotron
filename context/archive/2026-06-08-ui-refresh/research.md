---
date: 2026-06-08T14:52:02+02:00
researcher: Michał Leśniewski
git_commit: 9fccba28e62aa180f07af155ffc3b602abc504fd
branch: ui-refresh
repository: korpotron
topic: "Modern CSS framework to replace Bootstrap (SSR, no build, CDN, component-class)"
tags: [research, ui, css-framework, bootstrap, bulma, tabler, bootswatch, django]
status: complete
last_updated: 2026-06-08
last_updated_by: Michał Leśniewski
last_updated_note: "Added follow-up research comparing daisyUI to the shortlist"
tags_added: [daisyui, tailwind]
---

# Research: Modern CSS framework to replace Bootstrap

**Date**: 2026-06-08T14:52:02+02:00 **Researcher**: Michał Leśniewski **Git Commit**:
9fccba28e62aa180f07af155ffc3b602abc504fd **Branch**: ui-refresh **Repository**: korpotron

## Research Question

The project currently uses raw Bootstrap 5, which looks generic and boring. We want to modernize the UI to improve UX
**without changing the architecture**: keep server-side rendering (no SPA), no JS/CSS build step, load assets from a CDN
as today, allow small custom-CSS tweaks but rely primarily on the framework, and keep JS simple/minimal
(framework-provided JS acceptable if integration is light). Which framework should replace Bootstrap? Focus on **ease of
integration** and **what each framework offers**.

### Scope decisions (from the user, this session)

- **Integration style**: prioritize **component-class (Bootstrap-like)** frameworks — the add-a-class model — over
  classless or utility-first (Tailwind).
- **JS**: keep the existing hand-written vanilla JS; loading framework-provided JS is fine **as long as integration is
  trivial**.
- **Theming / dark mode**: **not a priority** for now — weight ease-of-integration and component coverage higher; defer
  theming to the design phase.

## Summary

> **⚠️ Superseded (2026-06-08):** This framework comparison is retained as historical context, but its Bootswatch
> recommendation is **no longer the plan**. A custom high-fidelity design was produced (`design_handoff/`) that **keeps
> raw Bootstrap 5** and adds a bespoke design system (`static/css/korpotron.css`, IBM Plex fonts). See the Decision
> section in `change.md`. No framework swap will happen.

The decisive factor is **migration cost**, because every template already uses Bootstrap classes and there is no build
step. That splits the candidate field cleanly:

- **Stay in the Bootstrap family** → existing markup, JS, and forms keep working; effort ranges from _one CDN line_
  (Bootswatch) to _an afternoon_ (Tabler).
- **Leave the Bootstrap family** (Bulma, Beer CSS, UIkit) → a fresher/more distinctive look but a **full re-class of
  every template** plus a new solution for Django form styling.

**Recommended shortlist (in order of effort):**

1. **Bootswatch** — a themed drop-in replacement for `bootstrap.min.css`. **Swap one CDN URL, change nothing else.**
   100% class-compatible, keeps the existing Bootstrap JS. A restyle, not a redesign — modern color/type/spacing, same
   component shapes. _Lowest risk and effort; the natural first step._
2. **Tabler** — a modern UI kit built **on** Bootstrap 5. Swap CSS + JS tags (its bundles include Bootstrap), reuse all
   existing Bootstrap classes, optionally adopt a few Tabler layout classes on the navbar/page shell. **Best modern look
   of any Bootstrap-based option.** _Pick this if "generic and boring" is the real complaint._
3. **Bulma** — clean, modern, **zero framework JS**, well-adopted. Full re-class required; has a Django form helper
   (`crispy-bulma`). _The choice if we want to leave the Bootstrap aesthetic entirely without going Material._
4. **Beer CSS** — genuine Material Design 3, the most "2026" look. Different naming model + a small JS module. _The
   choice for a bold, opinionated redesign._

UIkit is a strong, polished framework but is the **worst fit for this app** specifically: heavy `uk-*`-attribute
migration, a required JS bundle, and **no maintained Django form helper**. Several once-popular options are **dead in
2026** — avoid Spectre.css, Pure.css, Cirrus; **Shoelace was archived 2026-03-24** (succeeded by Web Awesome). Web
Awesome / Material Web are **web components**, not an add-a-class model — out of scope.

A cross-cutting note: the app renders forms with `{{ form.as_p }}`, which **Bootstrap does not auto-style either** — so
form fields are already semi-unstyled today. Staying in the Bootstrap family therefore introduces **no form regression
and no new form work**; leaving it makes solving Django form styling mandatory.

## Detailed Findings

### Current UI surface (live codebase)

Small, cohesive Django SSR app. Bootstrap 5.3.3 loaded from jsDelivr; **no `static/` CSS file exists yet**; all styling
is inline Bootstrap classes; interactivity is hand-written vanilla JS.

- `templates/base.html:7` — Bootstrap 5.3.3 `<link>` (jsDelivr, SRI hash). Dark `navbar`, `container` layout,
  `{% block content %}`. **No Bootstrap JS bundle is loaded at all** — the app currently uses zero Bootstrap JS
  components.
- `templates/core/landing.html:7` — standalone page (does **not** extend base), duplicates the Bootstrap `<link>` with a
  "version must match base.html" comment. Dark hero, `display-3`, `lead`, `btn btn-primary btn-lg`.
- `templates/core/generate.html` — the interactive heart. Uses `row`/`col-lg-6`, `form-label`, `form-select`,
  `form-control`, a **single-select toggle `btn-group`** of `btn-outline-primary` buttons (`generate.html:31-39`),
  `spinner-border` (`generate.html:47`), `alert alert-danger` (`generate.html:55`), and ~150 lines of vanilla JS doing
  `fetch` to the generate API, button-group toggle logic, and clipboard copy (`generate.html:69-216`). **This is the
  file most sensitive to a class migration.**
- `templates/core/template_list.html` / `optiongroup_list.html` — `table`, `btn-sm btn-outline-*`,
  `d-flex justify-content-between`.
- `templates/core/template_form.html`, `optiongroup_form.html`, `registration/login.html`, the two
  `*_confirm_delete.html` — forms via `{{ form.as_p }}`, `btn btn-primary` / `btn-danger` / `btn-outline-secondary`.
- `templates/core/optiongroup_form.html` — dynamic formset: `border rounded p-3` rows, `<template>` cloning,
  add/delete-row vanilla JS (`optiongroup_form.html` script block).

**Bootstrap components actually in use** (the compatibility yardstick): navbar, grid (`row`/`col`), form controls
(`form-control`/`form-select`/`form-label`), buttons + variants, single-select toggle `btn-group`, `spinner-border`,
`alert`, `table`, bordered panels (`border rounded`), display/hero headings (`display-3`, `lead`). No modals, dropdowns,
offcanvas, tooltips — i.e. **no JS-dependent Bootstrap components today**.

### Tier 1 — Stay in the Bootstrap family (lowest migration cost)

#### Bootswatch — one-line restyle, zero template changes

- **Version**: 5.3.8 (built for Bootstrap 5.3); MIT, actively maintained (thomaspark/bootswatch). 28 themes.
- **No build step**; single CDN `<link>` that is a 1:1 drop-in replacement for the official `bootstrap.min.css`:
  ```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootswatch@5.3.8/dist/flatly/bootstrap.min.css" />
  ```
  (swap `flatly` for any theme name; keep any Bootstrap JS bundle unchanged — Bootswatch ships no JS).
- **Markup compatibility**: **100%** — same class names, same DOM. Zero template edits.
- **Modern theme picks (2026)**: Flatly (flat/modern), Lux (airy, uppercase), Minty, Zephyr, Simplex, Cosmo; niche:
  Quartz (glassmorphic), Morph (neumorphic), Vapor (synthwave).
- **Trade-off**: a _restyle_, not a _redesign_ — component shapes stay Bootstrap. Refreshes the "generic" feel but won't
  look as distinctive as Tabler/Bulma/Beer.
- **Effort to update SRI**: the current `<link>` carries an `integrity` hash (`base.html:7`); a themed URL needs its own
  hash or the attribute removed. Trivial but must not be missed (also applies to the duplicated link in
  `landing.html:7`).

#### Tabler — modern look, still Bootstrap underneath

- **Version**: v1.4.0 (2025-07-13), bundles Bootstrap 5.3.7; very active (tabler/tabler, ~40k★), MIT.
- **Architecture**: `tabler.min.css` **contains a compiled copy of Bootstrap** + Tabler's design layer (so you do
  **not** also load `bootstrap.min.css`); `tabler.min.js` bundles Bootstrap's JS + Tabler add-ons (vanilla, no jQuery,
  no build).
  ```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/core@1.4.0/dist/css/tabler.min.css" />
  <script src="https://cdn.jsdelivr.net/npm/@tabler/core@1.4.0/dist/js/tabler.min.js"></script>
  ```
- **Migration**: reuses standard Bootstrap class names (`btn btn-primary`, `row`, `col`, `card`, `form-control`,
  `table`, `alert`, `spinner-border`, `navbar`…) so existing markup restyles **for free**. To look genuinely "Tabler"
  (vs "nicer Bootstrap"), the navbar/page shell benefits from a few Tabler layout classes (`page-header`, `navbar-*`,
  etc.) — an afternoon of optional shell work, mostly in `base.html`.
- **Look**: the most contemporary of the Bootstrap-based options (clean app/dashboard aesthetic, refined spacing, icon
  set, good dark mode). **Superset of Bootstrap** components.
- **Note**: Tabler is dashboard-flavored; for a small app you simply ignore the dashboard shell classes you don't need.

#### Halfmoon — drop-in with dark mode, but quiet maintenance

- **Version**: v2.0.2 (2024-09-03); MIT, ~3k★, **low cadence** (last release ~21 months ago as of 2026-06). "Drop-in
  Bootstrap replacement," same class names, ships **no JS** (relies on Bootstrap's bundle), strong CSS-variable
  theming + built-in dark mode.
  ```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/halfmoon@2.0.2/css/halfmoon.min.css" />
  ```
- **Verdict**: a near-zero-effort drop-in like Bootswatch, attractive in dark mode, but the slowing project and possible
  lag behind the newest Bootstrap 5.3 utilities push it below Bootswatch/Tabler. Reach for it only if **dark mode**
  becomes a priority (it isn't, per scope).

#### Other Bootstrap-based kits (brief)

- **AdminLTE 4** (v4.0.0, on Bootstrap 5.3.8, no jQuery, very active) — an **admin dashboard shell** (sidebar layout).
  Overkill for a small SSR app unless we want a dashboard.
- **MDB free** (v9.2.0, Material-on-Bootstrap) — modern Material look but **gates many components behind a paid tier**;
  its JS replaces Bootstrap's. Licensing friction.
- **Bootstrap Italia** — purpose-built for Italian public-administration design; CDN "not recommended for production."
  Wrong fit.

### Tier 2 — Leave the Bootstrap family (full re-class, fresher look)

#### Bulma 1.0.4 — clean, zero JS, has a Django form helper

- **Version**: 1.0.4 (2025-04-19); ~50k★, ~382k npm downloads/week — **the most adopted** of the non-Bootstrap
  candidates. Maintained but slow cadence (single-maintainer, CSS-only so less churn needed). v1 adds CSS custom
  properties (theme via plain CSS, no Sass).
- **No build step**, **ships zero JavaScript** — interactive bits (navbar burger, notification dismiss) are 5–15 line
  vanilla handlers you write. **Never competes with the app's own JS** — best fit for the "keep our vanilla JS"
  preference.
  ```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.4/css/bulma.min.css" />
  ```
- **Component coverage** maps ~1:1 onto the app's needs: `navbar`, `columns`/`column`,
  `input`/`textarea`/`select`/`field`/`control`, `button is-*`, **`buttons has-addons`** (the segmented toggle),
  `button is-loading` (spinner-as-modifier — works on `<button>`, not `<input type=submit>`), `notification`,
  `table is-striped`, `card`/`box`, `hero`/`title`.
- **Migration**: **full re-class** (no class overlap with Bootstrap), but predictable `component is-modifier` grammar.
  Examples: `btn btn-primary`→`button is-primary`; `row`/`col-md-6`→`columns`/`column is-half`;
  `alert alert-warning`→`notification is-warning`; `spinner-border`→`button is-loading`.
- **Django forms**: `crispy-bulma` 0.12.0 (django-crispy-forms pack, ckrybus/crispy-bulma) gives `{% crispy form %}`
  with Bulma markup — but **PyPI flags it Inactive**; pin and verify against Django 6.0.

#### Beer CSS 4.0.21 — Material Design 3, the most modern look

- **Version**: 4.0.21, active; real MD3 ("Expressive"). The most "2026" aesthetic of the field.
  ```html
  <link href="https://cdn.jsdelivr.net/npm/beercss@4.0.21/dist/cdn/beer.min.css" rel="stylesheet" />
  <script type="module" src="https://cdn.jsdelivr.net/npm/beercss@4.0.21/dist/cdn/beer.min.js"></script>
  <script
    type="module"
    src="https://cdn.jsdelivr.net/npm/material-dynamic-colors@1.1.4/dist/cdn/material-dynamic-colors.min.js"
  ></script>
  ```
- **Add-a-class** but with **MD3 vocabulary** (`<nav>`, `<article>` as cards) rather than Bootstrap names — a different
  mental model. Ships a small JS module (ripples, dynamic color). No build step. Strong coverage (app-bar/nav, grid,
  forms, buttons, progress, snackbar/alert, tables, cards). **No crispy pack** — forms styled via django-widget-tweaks.
- **Verdict**: pick for a bold, opinionated Material redesign; highest visual payoff, highest divergence from current
  markup.

#### UIkit 3.25.x — rich and polished, but the worst fit here

- **Version**: 3.25.17 (May 2025; v3 line maintained, YOOtheme-backed, no jQuery, no build). CDN = CSS +
  `uikit.min.js` + `uikit-icons.min.js`.
- **Richer out-of-the-box** than Bulma (built-in `uk-spinner`, dismissible `uk-alert`, toast `UIkit.notification()`,
  polished cards, icon system) and arguably the most premium look.
- **Why it's the worst fit for _this_ app**: (1) many components are **JS-driven**, so you load a ~tens-of-KB framework
  bundle; (2) migration is heavier because components need `uk-*` **attributes**, not just class swaps (not a pure
  find-replace); (3) **no maintained crispy-forms pack** for Django.

### Dead / out-of-scope (verified June 2026)

- **Spectre.css** — original repo unmaintained, never hit 1.0. **Avoid.**
- **Pure.css** — 3.0.0 (~3 yrs old), npm flags inactive/discontinued, minimal components. **Avoid.**
- **Cirrus CSS** — release cadence stalled; questionable. **Avoid betting on it.**
- **Shoelace** — **repository archived 2026-03-24**, read-only; superseded by **Web Awesome**. **Don't start new work on
  it.**
- **Web Awesome / Material Web** — **web components** (`<wa-button>`, `<md-…>`), not an add-a-class model; hard JS
  dependency + FOUC risk under SSR. **Out of scope per the chosen style.**
- **Fomantic-UI** — maintained (the Semantic UI fork), comprehensive, but **requires jQuery** for interactive components
  — conflicts with the minimal-vanilla-JS goal. Only if jQuery is acceptable.
- **daisyUI / Tailwind** — utility-first and effectively needs a build. **Out of scope per the chosen style.**

### Cross-cutting: styling Django `{{ form.as_p }}` without a build step

`as_p` emits bare `<input>/<select>/<textarea>/<label>` with **no classes**. Component-class frameworks (Bootstrap,
Bulma, UIkit, Beer CSS) **do not style raw form elements** — so forms need per-widget classes regardless. All bridges
below are **pure server-side Python — no build step**:

1. **django-crispy-forms 2.6** (2026-03-19, stable) + a template pack — swap `as_p` → `{{ form|crispy }}`, pack applies
   framework classes/wrappers.
   - `crispy-bootstrap5` **2026.3** (2026-03-01) — best-maintained pack. (Relevant if we stay Bootstrap and want the
     forms _also_ properly styled, which they aren't today.)
   - `crispy-bulma` 0.12.0 (2025-05) — usable but **flagged Inactive**; pin + verify.
   - No official pack for Beer CSS / UIkit / Fomantic.
2. **django-widget-tweaks 1.5.1** (2026-01-02) — template-level `{{ form.x|add_class:"input" }}` / `{% render_field %}`.
   The no-build bridge of choice when **no crispy pack exists** (Beer CSS, UIkit). ⚠️ Declared support tops out at
   Django 5.2; **CLAUDE.md says Django 6.0.5 — verify before relying on it.**
3. **Manual widget `attrs={"class": …}`** in `forms.py` — zero deps, verbose, reliable.
4. **Django's own form renderer / `__init__` class-injection / custom field templates** — most control, most work; good
   for wrapper-heavy frameworks (Bulma `field/control`).

**Key implication**: because the app's forms are **already unstyled under Bootstrap**, the "stay Bootstrap" options
(Bootswatch/Tabler) carry **no new form work** to ship a refresh — form polish can be a separate, optional follow-up
(crispy-bootstrap5). The "leave Bootstrap" options make a form bridge **mandatory** as part of the migration.

## Code References

- `templates/base.html:7` — Bootstrap 5.3.3 CDN `<link>` with SRI hash; the single swap-point for any Bootstrap-family
  restyle. No Bootstrap JS bundle is loaded.
- `templates/core/landing.html:7` — **duplicate** Bootstrap `<link>` (page doesn't extend base); any CDN change must
  touch this too. Candidate to refactor to extend `base.html`.
- `templates/core/generate.html:31-39` — single-select toggle `btn-group`; the trickiest component to re-class (Bulma
  `buttons has-addons`, etc.).
- `templates/core/generate.html:47` — `spinner-border` (maps to `button is-loading` in Bulma).
- `templates/core/generate.html:69-216` — hand-written vanilla JS (fetch, toggle, clipboard) that must keep working
  under any framework; argues for CSS-only or trivially-additive JS.
- `templates/core/optiongroup_form.html` — formset rows (`border rounded p-3`) + add/delete vanilla JS; `border rounded`
  utilities need framework equivalents off-Bootstrap.
- `templates/core/template_form.html`, `optiongroup_form.html`, `registration/login.html`, `*_confirm_delete.html` —
  `{{ form.as_p }}` forms (already unstyled under Bootstrap).

## Architecture Insights

- **Migration cost is dominated by class-name compatibility**, and the app is small but class-dense, with one JS-coupled
  page (`generate.html`). This makes "stay in the Bootstrap family" disproportionately cheap and low-risk.
- **The app loads no Bootstrap JS today** — there are no modals/dropdowns to port. So the "framework ships JS" concern
  only matters if we _adopt_ JS-driven components; CSS-only frameworks (Bulma) or restyles (Bootswatch) keep the JS
  footprint exactly as it is.
- **`landing.html` duplicates the CSS link** and bypasses `base.html`; whatever we pick, the refresh should consolidate
  the asset reference (single source of truth for the CDN URL), matching the existing "version must match base.html"
  comment's intent.
- **Custom CSS hook is missing**: there is no `static/css` file yet. Any framework choice pairs naturally with adding
  one small project stylesheet for the "small tweaks" the brief allows.
- **SRI hashes** on the CDN links are an integration detail: themed/alternate CDN URLs need their own `integrity` value
  or the attribute dropped.

## Historical Context (from prior changes)

- `context/foundation/lessons.md` — "Verify Docker build before committing" and "Sync GitHub issues with context
  changes." Both apply to the eventual implementation change (a CDN/CSS swap still goes through Docker build + issue
  sync), not to framework selection itself.
- No prior `context/changes/**` or `context/archive/**` research on UI/CSS exists; this is the first UI-refresh
  exploration. The change folder `context/changes/ui-refresh/` was initialized at commit `9fccba2` and advanced to
  `status: preparing` by this research.

## Related Research

- None yet — this is the first research artifact for the `ui-refresh` change.

## Open Questions

1. **Restyle vs redesign**: Is the goal "less generic, minimal effort" (→ Bootswatch / Tabler, stay Bootstrap) or
   "distinctly different / modern identity" (→ Bulma / Beer CSS, full re-class)? This is the single decision that gates
   the plan.
2. **Appetite for re-classing every template** (incl. the JS-coupled `generate.html`) if we leave the Bootstrap family.
3. **Should the refresh also fix form styling** (forms are unstyled today), or keep that as a separate follow-up?
   Determines whether crispy-forms / widget-tweaks enters scope now.
4. **Django 6.0 compatibility** of any Python form helper we adopt (django-widget-tweaks declares support only through
   5.2; crispy-bulma is flagged inactive).
5. **`landing.html` consolidation**: fold it into `base.html` (or a shared head partial) as part of the refresh, so the
   CDN reference lives in one place?
6. Exact theme/aesthetic direction (deferred by the user to after framework selection).

## Follow-up Research 2026-06-08T15:00:00+02:00 — daisyUI

**Question**: Add daisyUI to the comparison.

### What daisyUI is

daisyUI is **not a standalone framework — it is a Tailwind CSS plugin** that adds an **add-a-class component layer**
(`btn`, `card`, `navbar`, `alert`, `table`, `input`, `select`…) on top of Tailwind's utility engine. The component model
itself is exactly the "Bootstrap-like" style you asked for — by coincidence some names even match Bootstrap
(`btn btn-primary`). The catch is everything _underneath_ it: layout, spacing, and sizing still come from **Tailwind
utilities**, not from daisyUI.

- **Version**: v5 (latest ~5.0.50, June 2026); very actively maintained, the most popular Tailwind component library
  (~40k★).
- **Themes**: excellent built-in theming (`data-theme="light|dark|…"`, 30+ themes) — but theming is not a priority per
  scope.

### Can it run with NO build step? Yes — but via the Tailwind **browser runtime**

daisyUI v5 ships an official CDN/no-build path (verified against daisyui.com/docs/cdn):

```html
<link href="https://cdn.jsdelivr.net/npm/daisyui@5" rel="stylesheet" type="text/css" />
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
```

The critical detail is the **second line**: `@tailwindcss/browser@4` is a **JavaScript runtime that compiles Tailwind
CSS in the browser** — it scans the DOM on load and generates utility CSS on the fly. Tailwind's own docs state the
browser/Play CDN is for **development and prototyping, not production**. Consequences:

- It's a **JS dependency that builds your CSS client-side** — a flash-of-unstyled-content on load, a runtime perf/scan
  cost, and exactly the kind of non-trivial JS the brief wanted to avoid. This is heavier and more "magic" than the
  framework JS in UIkit/Tabler (which only drive widgets, not your stylesheet).
- It contradicts "load CSS from a CDN just like now": today a single static `bootstrap.min.css` arrives ready-to-use;
  here a JS engine must _manufacture_ the CSS in every visitor's browser.

**Alternative no-runtime path** — load _only_ the daisyUI CSS link and drop the Tailwind script. Then you get daisyUI's
**components** but **none of Tailwind's layout/spacing utilities** (`grid`, `flex`, `gap-4`, `mb-3`, `w-1/2`…). daisyUI
provides **no grid system** of its own, so you'd hand-write custom CSS for all layout — defeating "rely on what the
framework brings." Not viable for the app's `row`/`col`/`d-flex`/`mb-3`-heavy markup.

**The "proper" daisyUI path is a build step**, which the brief rejects. For Django there is a clean middle option —
**`django-tailwind-cli`** (uses Tailwind's standalone binary, **no Node**, with hot reload, production builds, and
daisyUI support). But that _is_ a build step (a self-contained one). It would be the right answer **only if the no-build
constraint were relaxed**.

### Migration & Django-form fit

- **Migration from Bootstrap**: full re-class. Components map reasonably (`btn btn-primary`, `alert`, `table`, `card`,
  `input`), but **layout flips from Bootstrap to the Tailwind paradigm**:
  `row`/`col-lg-6`→`grid grid-cols-1 lg:grid-cols-2 gap-4`, `d-flex justify-content-between`→`flex justify-between`,
  `mb-3`→`mb-3` (Tailwind, different source), `btn-group`→daisyUI `join`. So it's heavier than a pure component swap —
  you adopt a whole utility vocabulary.
- **Django forms**: same per-widget-class problem as the others; **no crispy-daisyUI pack** (`crispy-tailwind` exists
  but emits raw Tailwind utilities, not daisyUI component classes). You'd use **django-widget-tweaks** to add
  `input`/`select`/`textarea` classes.
- **The app's vanilla JS** (`generate.html`) keeps working — daisyUI/Tailwind don't touch it.

### Where daisyUI lands vs the shortlist

| Option         | No build?                                | CSS delivery                                      | Add-a-class                          | Migration from BS                             | JS footprint                               | Django forms                           |
| -------------- | ---------------------------------------- | ------------------------------------------------- | ------------------------------------ | --------------------------------------------- | ------------------------------------------ | -------------------------------------- |
| **Bootswatch** | ✅ true                                  | static CSS                                        | ✅ (=Bootstrap)                      | **~zero** (swap URL)                          | unchanged                                  | unchanged (crispy-bs5 optional)        |
| **Tabler**     | ✅ true                                  | static CSS                                        | ✅ (Bootstrap+)                      | low (shell tweaks)                            | +1 vanilla bundle                          | unchanged                              |
| **Bulma**      | ✅ true                                  | static CSS                                        | ✅                                   | full re-class                                 | **zero**                                   | crispy-bulma (inactive)                |
| **Beer CSS**   | ✅ true                                  | static CSS                                        | ✅ (MD3 names)                       | full re-class (MD3)                           | small JS module                            | widget-tweaks                          |
| **daisyUI**    | ⚠️ only via **Tailwind browser runtime** | **JS-compiled at runtime** (or custom-CSS layout) | ✅ components, ❌ layout (=Tailwind) | full re-class **+ Tailwind utility paradigm** | **Tailwind runtime JS** (prod-discouraged) | widget-tweaks (no daisyUI crispy pack) |

### Verdict on daisyUI

daisyUI's **component layer is genuinely modern and exactly the add-a-class style requested**, and it's the most
theme-rich option. But against **this project's hard constraints** it is the **weakest of the modern candidates**: the
only honest no-build path relies on the **Tailwind browser runtime**, which Tailwind itself flags as not-for-production
and which replaces today's "ready-made CSS from a CDN" with "CSS manufactured by JS in the browser" — the opposite of
the minimal-JS, CDN-delivered goal. Stripping the runtime leaves you without a layout system.

- **If the no-build rule is firm** → prefer **Bootswatch/Tabler** (Bootstrap-compatible, true static CSS) or **Bulma**
  (zero JS) over daisyUI.
- **daisyUI only becomes the right call if the team accepts a (Node-free) build step** via **`django-tailwind-cli`** —
  at which point it's excellent: modern components, great themes, proper production CSS. That is a deliberate trade of
  the no-build constraint for daisyUI's polish, and worth a separate decision if appetite exists.

### New open question

7. **Is the "no build step" constraint firm, or open to a Node-free build** (Tailwind standalone binary via
   `django-tailwind-cli`)? This is the single condition under which daisyUI moves from "weakest fit" to "strong
   contender." If firm, daisyUI is dominated by Bootswatch/Tabler/Bulma.
