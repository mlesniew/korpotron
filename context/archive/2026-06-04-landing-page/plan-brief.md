# Landing Page — Plan Brief

> Full plan: `context/changes/landing-page/plan.md`

## What & Why

Add a public landing page so unauthenticated visitors have a meaningful entry point instead of an immediate redirect to the login form. The root URL `/` becomes auth-aware: anonymous users see a branded hero page; authenticated users skip it and land on the generate UI as before.

## Starting Point

Today, `/` maps to `GenerateView` (LoginRequiredMixin), so unauthenticated requests get 302'd straight to `/accounts/login/`. There is no public-facing content anywhere in the app.

## Desired End State

An unauthenticated visitor hitting `https://korpotron.fly.dev/` sees a full-viewport dark page with the Korpotron name, a short tagline about the product, and a "Get started" button leading to the login form. After logging in they land on the generate UI exactly as today. Authenticated users visiting `/` directly skip the landing page entirely.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
|---|---|---|
| URL routing | Keep `/`, dispatch in one view | Avoids URL changes and bookmark breakage for existing logged-in users |
| Landing template | Standalone (no base.html) | Full-viewport hero look isn't achievable within the dark navbar + container layout |
| Navbar on landing | None | Minimal — single CTA is the sole entry point, no need for persistent nav |
| Copy | Placeholder drafted in plan | Unblocks implementation; easy one-line edit in the template later |
| Test strategy | Fix broken assertions + add 2 new tests | Full coverage of both auth-dispatch branches |

## Scope

**In scope:**
- New `HomeView` that replaces `GenerateView` as the `/` handler
- Standalone `templates/core/landing.html` (Bootstrap 5, dark hero, "Get started" CTA)
- Two fixed test assertions + two new tests

**Out of scope:**
- URL changes (no GenerateView relocation)
- Auth settings changes (`LOGIN_REDIRECT_URL`, `LOGIN_URL` unchanged)
- Registration/signup flow
- Mobile layout

## Architecture / Approach

`GenerateView` (LoginRequiredMixin + TemplateView) is replaced by `HomeView` (plain `View`, no mixin). The `get()` method branches on `request.user.is_authenticated`: anonymous → render `core/landing.html`; authenticated → query templates + option groups, render `core/generate.html`. URL name `"home"` is preserved throughout. No settings changes.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. View & routing | `HomeView` dispatches on auth state | No `LoginRequiredMixin` — anonymous access to `/` is now intentional; confirm tests are updated in Phase 3 |
| 2. Landing template | Standalone hero page with CTA | Copy is placeholder — needs final wording before or after implementation |
| 3. Test updates | All tests green, two new assertions | Two existing tests break if Phase 3 runs before Phase 1 |

**Prerequisites:** none beyond the current working app  
**Estimated effort:** ~1 short session across 3 phases

## Open Risks & Assumptions

- Placeholder copy in the template is a draft — the tagline should be reviewed and edited to match the author's voice
- Docker build check (from lessons.md) should be run after implementation before committing

## Success Criteria (Summary)

- `uv run pytest` passes with no failures after all three phases
- Anonymous `GET /` returns 200 with hero content; clicking "Get started" reaches `/accounts/login/`
- Authenticated `GET /` renders the generate UI unchanged
