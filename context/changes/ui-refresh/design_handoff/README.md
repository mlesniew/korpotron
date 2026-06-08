# Design Handoff: Korpotron UI Redesign

## Overview

This package contains high-fidelity HTML design references for a full redesign of the
Korpotron Django application. All views have been redesigned: landing page, login,
generate (core), templates list/form, and modifiers (option groups) list/form.

## About the Design Files

The `.html` files in this folder are **design references** — interactive prototypes
showing the intended look, feel, and behaviour. They are **not** production code.

Your task is to **recreate these designs in the existing Django + Bootstrap codebase**
by replacing the Django templates (`templates/` directory) with ones that match these
references. Use Bootstrap 5 utilities and components where possible, supplementing
with custom CSS for anything Bootstrap doesn't cover (the design system tokens below).

Do **not** copy the HTML files directly into the project — they use static dummy data
and prototype-only JS. Wire everything to Django template tags, form rendering, and
URL reversals as appropriate.

## Fidelity

**High-fidelity.** Match the designs pixel-closely: exact colours (CSS custom
properties listed below), font stack, spacing, border radii, shadows, and interaction
states (hover, focus, active). The prototypes are interactive — open them in a browser
to see hover states, transitions, and JS behaviour.

---

## Design System Tokens

Add these to a `static/css/korpotron.css` file and load it from `base.html` (after
Bootstrap). Override Bootstrap variables where they conflict.

```css
:root {
  /* Palette */
  --k-bg:           oklch(97% 0.008 85);      /* page background */
  --k-surface:      #fff;                      /* card / panel background */
  --k-surface-2:    oklch(98.5% 0.005 85);    /* subtle alternate surface */
  --k-border:       oklch(90% 0.007 80);       /* default border */
  --k-border-s:     oklch(83% 0.009 80);       /* stronger border */

  /* Text */
  --k-text:         oklch(14% 0.01 270);       /* primary text */
  --k-text-mid:     oklch(50% 0.012 270);      /* secondary text */
  --k-text-dim:     oklch(70% 0.008 270);      /* muted / placeholder text */

  /* Accent (amber) */
  --k-accent:       oklch(61% 0.16 40);
  --k-accent-h:     oklch(55% 0.16 40);        /* hover */
  --k-accent-bg:    oklch(94% 0.055 40);       /* tinted background */
  --k-accent-txt:   oklch(32% 0.12 40);        /* text on tinted bg */

  /* Navigation */
  --k-nav:          oklch(14% 0.012 270);      /* navbar background */
  --k-nav-text:     oklch(93% 0.005 80);
  --k-nav-dim:      oklch(55% 0.008 270);

  /* Danger */
  --k-danger:       oklch(52% 0.18 22);
  --k-danger-bg:    oklch(96.5% 0.04 22);
  --k-danger-b:     oklch(87% 0.08 22);

  /* Success */
  --k-ok:           oklch(55% 0.15 150);
  --k-ok-bg:        oklch(96% 0.04 150);

  /* Radii */
  --k-r:            7px;
  --k-r-lg:         11px;
  --k-r-xl:         15px;

  /* Shadows */
  --k-shadow-sm:    0 1px 3px rgba(0,0,0,.05), 0 1px 2px rgba(0,0,0,.04);
  --k-shadow-md:    0 4px 20px rgba(0,0,0,.09), 0 2px 6px rgba(0,0,0,.05);
}
```

### Typography

```html
<!-- Add to <head> in base.html -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

```css
body { font-family: 'IBM Plex Sans', system-ui, sans-serif; }

/* Brand name and Generate button only */
.k-mono { font-family: 'IBM Plex Mono', monospace; }
```

---

## Screens

### 1. Landing Page — `Korpotron Landing.html`

**File:** `templates/core/landing.html`

- Full-viewport dark hero (`background: oklch(11% 0.012 270)`) with a subtle CSS grid
  overlay and amber radial glow (pure CSS, no images needed).
- Fixed frosted-glass nav (`backdrop-filter: blur(10px)`) with brand name left, Log in
  button right.
- Hero copy: headline in IBM Plex Mono, subheading in IBM Plex Sans at 16px/1.75.
- Three feature tiles in a bordered strip below the CTA — flex row, equal-width
  columns, separated by 1px borders. Each tile shows a category label (in accent
  colour, uppercase mono), a bold title, and a short description.
- **Login:** rendered as a modal overlay (not a separate page). The "Log in" button
  and "Log in to get started →" CTA both open it. The overlay has a blurred backdrop,
  a centred card with username + password fields and a submit button. Closes on
  Esc or clicking the backdrop.
  - In Django: the overlay form POSTs to `{% url 'login' %}`. On the page itself,
    render the login form inside the overlay markup and show any `form.errors` inline.

### 2. Login — `Korpotron Login.html`

**File:** `templates/registration/login.html`

This is the standalone login page Django serves when `@login_required` redirects
an unauthenticated user. It matches the modal card from the landing page exactly,
but rendered as a full page.

- Same dark background and subtle CSS grid as the landing page.
- Minimal fixed nav: brand name only (links back to landing), no other links.
- Centred login card (max-width 360px): title + subtitle in the header, username +
  password fields + submit button in the body.
- Error bar (shown when `form.errors` is non-empty): dark red tinted, lists errors.
- "← Back to home" link below the card.
- The form POSTs to `{% url 'login' %}` with `{% csrf_token %}`; Django's auth view
  handles validation and redirect.

### 3. Generate — `Korpotron Generate.html`

**File:** `templates/core/generate.html`

**Layout:** Single column, max-width 1120px, centred.

**Section 1 — Template selector**
- Label row: "Template" (uppercase, 10.5px, dimmed) + "Manage →" link right-aligned
  pointing to `{% url 'template-list' %}`.
- Pill buttons (`.tmpl-btn`): `padding: 7px 16px`, `border-radius: 99px`,
  `border: 1.5px solid var(--k-border-s)`. Active state: accent border + accent tinted
  background. Each pill shows the template name. A dashed "+ New template" pill at the
  end links to `{% url 'template-create' %}`.
- Selecting a template stores `template_id` for the API call. Default: first template.
- If no templates exist, show a prompt: "No templates yet. [Create one →]"

**Section 2 — Modifiers**
- Label row: "Modifiers" + "Manage →" link to `{% url 'option-group-list' %}`.
- One row per `OptionGroup`. Each row: right-aligned group name label (12px, semibold,
  min-width 76px) + pill buttons for each `Option`. Radio behaviour within each group
  (one selection max, clicking the active option deselects it).
- If no option groups exist, omit this section entirely.

**Divider:** `<hr>` styled as `border-top: 1px solid var(--k-border)`.

**Section 3 — Input / Output workspace**
- **Input state** (default): label "Text to transform", `<textarea>` full-width,
  min-height 180px, border-radius `var(--k-r-xl)`. Below it: amber Generate button,
  full-width, IBM Plex Mono font.
- **Generate API call:** POST to `{% url 'generate' %}` (the `generate_api` view) with
  JSON body `{ template_id, option_ids: [...], text }`. While waiting, replace the
  input section with the output card showing a spinner + rotating buzzword message.
  On success, transition to output state.
- **Output state** (after generation): hide the textarea; show the output card (white
  surface, bordered, border-radius `var(--k-r-xl)`) with "← Edit text" + "↻ Regenerate"
  controls above it. The card shows Title (if `generate_title` is true) and Result
  fields, each with a small "Copy" button. A full-width "Copy to clipboard" button
  sits below the card.
- **Loading quips** (rotate randomly during generation):
  "Leveraging core competencies…", "Synergising the deliverables…",
  "Aligning stakeholder objectives…", "Actioning the key takeaways…",
  "Pivoting the bandwidth…", "Boiling the ocean…", "Moving the needle…",
  "Operationalising the value-add…", "Circling back on synergies…"

**Error handling:** Show an amber-bordered error bar above the Generate button for
client-side validation (empty text, no template). For API errors (4xx/5xx from
`generate_api`), show the error message from the JSON response in the same bar.

### 3. Templates List — `Korpotron Templates.html`

**File:** `templates/core/template_list.html`

- Page header: "Templates" (20px, bold) + count of templates (13px, dimmed) inline,
  "+ New template" accent button right.
- List container: white card, `border: 1.5px solid var(--k-border)`,
  `border-radius: var(--k-r-xl)`. Each row separated by 1px border.
- Each row (`.tmpl-row`): hover background `var(--k-surface-2)`.
  - Left: template name (bold, 14px) + optional "Generates title" badge (amber tinted
    pill, shown only when `template.generate_title` is True) + prompt preview (12.5px,
    dimmed, truncated with `text-overflow: ellipsis`).
  - Right: "Use →" link to `{% url 'home' %}?template={{ template.pk }}` (accent
    tinted pill), "Edit" link to `{% url 'template-update' template.pk %}`, "Delete"
    button (triggers custom delete dialog — see below).
- **Empty state:** dashed-border card, centred text, "+ New template" button.
- **Delete dialog:** Custom modal (not `confirm()`). Shows "Delete template?" title,
  template name in bold, Cancel + red Delete buttons. On confirm, the Django delete
  view handles the actual deletion; in the list, the row fades out.

### 4. Template Form — `Korpotron Template Form.html`

**File:** `templates/core/template_form.html`

- Breadcrumb: "Templates › Edit template" (or "New template").
- Form card: max-width 680px, white surface, bordered, `border-radius: var(--k-r-xl)`.
- **Name field:** single-line input, label "Name".
- **Prompt field:** label "Prompt" + right-aligned hint "Tells the AI how to transform
  the text". Large textarea, min-height 220px, resizable.
- **Generate title:** toggle switch (not a checkbox). Use a `<label>` wrapping a
  hidden `<input type="checkbox">` and a styled `<span>` track. Checked state:
  accent background. Sits inside a subtle tinted row with a plain-English description.
- Footer: "Save template" accent button + "Cancel" ghost button linking back to
  `{% url 'template-list' %}`.

### 5. Modifiers List — `Korpotron Modifiers.html`

**File:** `templates/core/optiongroup_list.html`  
*(rename "Option Groups" to "Modifiers" throughout — nav, headings, URLs can stay as-is
in Django, only the visible label changes)*

- Mirrors the Templates list layout exactly.
- Each row: modifier name (bold) + inline option pills showing all `Option.name` values
  for that group (neutral pills, no accent on first child — all identical).
- Actions: "Edit" link to `{% url 'option-group-update' group.pk %}`, "Delete" button
  (custom dialog — same pattern as templates).
- Empty state: same dashed-border pattern, copy adjusted for modifiers.

### 6. Modifier Form — `Korpotron Modifier Form.html`

**File:** `templates/core/optiongroup_form.html`

- Breadcrumb: "Modifiers › Edit modifier" (or "New modifier").
- Form card: max-width 760px (wider than template form to accommodate two-column rows).
- **Name field:** single-line input, max-width 320px.
- **Options formset:**
  - Column headers above the rows: "Label" (left) + "Instruction injected into prompt"
    (right) — both 10.5px uppercase dimmed.
  - Grid columns: `grid-template-columns: 180px 1fr 32px`.
  - Each option row: subtle tinted background (`var(--k-surface-2)`), 1.5px border,
    `border-radius: var(--k-r-lg)`. Focus-within: accent border.
    - Left: name input (font-weight 500, 13px).
    - Middle: instruction textarea (min-height 60px, 2 rows, resizable).
    - Right: × delete button (28×28px, hover: danger colour + tinted background).
  - Deletion: check the Django `DELETE` checkbox in the hidden formset field and hide
    the row with a fade-out transition.
  - "+ Add option" button: full-width dashed button, hover: accent tinted.
  - Management form (`{{ formset.management_form }}`) required for Django formset.
- Footer: "Save modifier" + "Cancel".

---

## Interactions & Behaviour

### Navigation
- Sticky nav, `height: 50px`, dark background `var(--k-nav)`.
- Brand: "KORPOTRON™" in IBM Plex Mono, `letter-spacing: .12em`.
- Nav links: dimmed by default, white + subtle bg on active/hover.

### Delete dialog (shared pattern)
Used on both Templates and Modifiers list pages. Implement once and reuse.

```html
<div class="k-del-overlay" id="del-overlay">
  <div class="k-del-dialog">
    <div class="k-del-title">Delete template?</div>
    <p>Are you sure you want to delete <strong id="del-name"></strong>?
       This cannot be undone.</p>
    <div class="k-del-actions">
      <button id="del-cancel">Cancel</button>
      <form method="post" id="del-form">
        {% csrf_token %}
        <input type="hidden" name="_method" value="post">
        <button type="submit" class="k-btn-danger">Delete</button>
      </form>
    </div>
  </div>
</div>
```

Wire each Delete button to set `del-form.action = {% url 'template-delete' pk %}`
and open the overlay. Close on Cancel or backdrop click.

### Copy to clipboard
```js
await navigator.clipboard.writeText(text);
// Flash button label to "Copied!" for 1300ms, then restore
```

### Generate API contract
```
POST /generate/   ({% url 'generate' %})
Content-Type: application/json

{
  "template_id": 3,
  "option_ids": [7, 12],   // one per group, or empty array
  "text": "raw input text"
}

200 OK → { "title": "...", "body": "..." }  // title may be null
400    → { "error": "..." }
429    → { "error": "daily limit message" }
502    → { "error": "generation failed message" }
```

### Toggle switch (CSS-only)
```html
<input type="checkbox" class="k-toggle-input" id="f-gen-title" name="generate_title">
<label class="k-toggle-track" for="f-gen-title"></label>
```
```css
.k-toggle-input { display: none; }
.k-toggle-track {
  display: block; width: 40px; height: 22px;
  background: var(--k-border-s); border-radius: 99px;
  position: relative; cursor: pointer; transition: background .2s;
}
.k-toggle-input:checked + .k-toggle-track { background: var(--k-accent); }
.k-toggle-track::after {
  content: ''; position: absolute; top: 3px; left: 3px;
  width: 16px; height: 16px; background: #fff; border-radius: 50%;
  transition: transform .2s; box-shadow: 0 1px 3px rgba(0,0,0,.2);
}
.k-toggle-input:checked + .k-toggle-track::after { transform: translateX(18px); }
```

---

## Files in This Package

| File | Django template to replace |
|---|---|
| `Korpotron Landing.html` | `templates/core/landing.html` |
| `Korpotron Login.html` | `templates/registration/login.html` |
| `Korpotron Generate.html` | `templates/core/generate.html` |
| `Korpotron Templates.html` | `templates/core/template_list.html` |
| `Korpotron Template Form.html` | `templates/core/template_form.html` |
| `Korpotron Modifiers.html` | `templates/core/optiongroup_list.html` |
| `Korpotron Modifier Form.html` | `templates/core/optiongroup_form.html` |

The `templates/registration/login.html` standalone page is now designed
(see `Korpotron Login.html`) to match the modal card on the landing page.

---

## Notes for Claude Code

- The design was built to complement Bootstrap 5, not replace it. Use Bootstrap grid
  and utility classes freely; add `korpotron.css` for colour tokens, typography,
  and custom components (pills, toggle switch, delete dialog, output card).
- `oklch()` colours are supported in all modern browsers. If you need IE11 fallbacks,
  convert to hex using the values in the token table above.
- The "Modifiers" label is a display rename only — all Django URL names and model
  names (`OptionGroup`, `option-group-*`) stay unchanged.
- The formset JS for the Modifier form (add/delete rows, update `TOTAL_FORMS`) should
  follow the existing pattern in `optiongroup_form.html` — just restyled.
