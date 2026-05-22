---
project: korpotron
researched_at: 2026-05-22
recommended_platform: Fly.io
runner_up: Railway
context_type: mvp
tech_stack:
  language: Python 3.12
  framework: Django 6.0.5
  runtime: Gunicorn (WSGI)
  database: Supabase (PostgreSQL, external)
  package_manager: uv
  llm_provider: OpenRouter (external)
---

## Recommendation

**Deploy on Fly.io with Supabase as the external database.**

Fly.io runs the Django app as a persistent Gunicorn process on a micro-VM — the exact execution model Django expects, with no serverless cold-start penalties on ORM connections or app registry initialization. Supabase provides managed PostgreSQL with a generous free tier and connects via a standard `DATABASE_URL`. The combination is the deployment target already identified in `tech-stack.md`, and the CLI (`flyctl`) covers all routine operations non-interactively. Estimated total cost: ~$5–10/month for the VM + shared IPv4; Supabase free tier at ~$0 for MVP traffic.

## Platform Comparison

| Platform | CLI-first | Managed/Serverless | Agent-readable docs | Stable deploy API | MCP/Integration | Total |
|---|---|---|---|---|---|---|
| **Fly.io** | Pass | Partial | Pass | Pass | Partial (experimental) | 3.5/5 |
| **Railway** | Pass | Pass | Partial | Pass | Pass (GA) | 4/5 |
| **Render** | Partial | Pass | Pass | Partial | Partial | 3/5 |
| Vercel | Pass | Pass | Pass | Pass | Pass | 5/5* |
| Netlify | — | FAIL (no WSGI) | — | — | — | Dropped |
| Cloudflare Workers | — | FAIL (Python beta, Django unsupported) | — | — | — | Dropped |

*Vercel scores 5/5 on generic agent-friendly criteria but ranks 4th on actual Django fit: Fluid Compute does not guarantee persistent state between requests, the Hobby CPU budget (4 hrs/month) is the binding constraint for Django apps, and the serverless model adds Django-specific configuration overhead that persistent-VM platforms avoid.

**Hard filters applied:** Netlify (serverless-only, no persistent WSGI process) and Cloudflare Workers (Python runtime in open beta, Django unsupported officially, V8 isolate model incompatible with WSGI) were dropped before scoring.

### Shortlisted Platforms

#### 1. Fly.io (Recommended)

Fly.io runs applications as persistent micro-VMs, not serverless functions. A Django/Gunicorn process stays alive between requests exactly as it would on a VPS. The `flyctl` CLI covers every routine operation (deploy, rollback via image tag, log tailing, secrets) with no interactive prompts and predictable exit codes. Official docs publish `llms.txt`; the `flyctl` source is open on GitHub. The main gaps vs. the runner-up: no free tier (trial only), `fly launch` does not auto-detect `uv` (a custom Dockerfile is required), and the MCP server is marked experimental. The `deployment_target: fly` hint in `tech-stack.md` reflects this being the intended destination from project inception.

#### 2. Railway

Railway's Nixpacks builder auto-detects `uv.lock` and provisions a Python 3.12 + uv environment with no Dockerfile required — the smoothest zero-to-deploy path for this stack. The CLI (`railway up`, `railway logs`, `railway variable set`) is comprehensive and non-interactive. An official MCP server is GA with Claude Code integration documented. Costs $5/month (Hobby). The one real gap is rollback: `railway rollback` does not exist as a CLI command; reverting a deploy requires the dashboard. This is Railway's primary operational weakness.

#### 3. Render

Render added native `uv` support to its Python runtime in June 2025 — `uv.lock` is auto-detected with no Dockerfile needed, the same as Railway. The `render` CLI covers deployments, logs, and env vars. `llms.txt` and `llms-full.txt` are published. An official MCP server is GA (August 2025) but has limited write operations: it cannot trigger deploys via MCP (CLI required). Cost is $7/month for the Starter web service tier; a free tier exists but spins down after 15 minutes of inactivity (~60s cold start on next request).

## Anti-Bias Cross-Check: Fly.io

### Devil's Advocate — Weaknesses

1. **No free tier.** The Hobby plan was deprecated in 2025. A minimal always-on app (shared-cpu-1x 512 MB + shared IPv4) costs ~$6/month from the first request. Railway's Hobby plan includes $5 of resource credit that covers very-low-traffic apps.
2. **`fly launch` does not detect uv.** The auto-generated Dockerfile uses pip/requirements.txt. A custom multi-stage Dockerfile (from the official `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` base image) is required before the first deploy. This is a one-time cost, but it's an extra step Railway avoids entirely.
3. **Auto-stop default causes cold starts.** `fly launch` generates `auto_stop_machines = "stop"` — the VM spins down after idle and restarts in several seconds on the next request. The fix (`min_machines_running = 1`, `auto_stop_machines = false`) is not prominent in the getting-started guide.
4. **No `fly rollback` command.** Reverting requires running `fly releases` to find the prior image tag, then `fly deploy --image registry.fly.io/<app>:<tag>`. More steps than a single command.
5. **MCP server is experimental.** `fly mcp server` carries the explicit `[experimental]` flag. Structured agent operations fall back to plain `flyctl` CLI, which works but lacks stable tool schemas.

### Pre-Mortem — How This Could Fail

The team deployed korpotron to Fly.io. Six months later it is a persistent source of friction. The problems accumulated in layers. The first deploy required a hand-written Dockerfile because `fly launch` generated a pip-based image that ignored the `uv.lock` file — an hour of debugging before a community forum post surfaced the fix. The auto-stop default wasn't caught during setup; the first real user hit a 6-second cold start, and the developer didn't notice for a week because local dev never cold-starts. After disabling auto-stop, the always-on VM plus shared IPv4 came to $8/month instead of the mentally budgeted $5.

When OpenRouter integration shipped, `fly secrets set OPENROUTER_API_KEY=...` worked fine but the running machine didn't pick up the new env var until a manual restart — a half-day of "why is the API key missing?" A migration failure mid-deploy left the schema in a forward-migrated state while the old container kept running, producing a 20-minute window of 500 errors. When an agent tried to instrument the platform, the experimental MCP server returned inconsistent results and the fallback CLI approach required ambient auth the agent didn't have in CI.

The cumulative effect: each problem is individually solvable, but the barrier to smooth operation is higher than expected for an MVP.

### Unknown Unknowns

- **IPv4 costs $2/month and is allocated by default.** Most new users are surprised when their "small app" costs $2 more than the VM price suggests. IPv6 is free but not universally supported.
- **`fly secrets set` does not restart the running machine.** The new env var is not visible to the live process until `fly deploy` or an explicit `fly machines restart`. The CLI gives no warning.
- **The `release_command` migration pattern has a partial-failure risk.** If a migration fails mid-deploy, Fly aborts starting the new version — but the schema change may already be applied. The old container continues running against a forward-migrated schema, which can cause errors until a rollback or fix is deployed.
- **Supabase free-tier projects are paused after 1 week of inactivity.** For a personal tool used sporadically, a holiday or busy week can mean returning to a paused database that requires a manual "restore project" step before the app works again. The fix is to upgrade to Supabase Pro ($25/month) or set up an uptime ping to prevent pausing.
- **`fly wireguard` required for local→Fly resource access.** Connecting a local dev environment to Fly-managed resources requires `fly proxy` or Wireguard tunnel setup. Not relevant with Supabase (external DB), but surprising the first time you need `fly ssh console`.

## Operational Story

- **Preview deploys**: Fly.io does not create automatic preview URLs per branch. A staging environment requires provisioning a second Fly app (`fly launch --name korpotron-staging`). GitHub Actions CI can deploy to staging on PR branches using a separate `fly.toml` and `FLY_API_TOKEN` secret scoped to the staging app.
- **Secrets**: All env vars live in Fly's encrypted secret store. Set with `fly secrets set KEY=value`; list with `fly secrets list`; remove with `fly secrets unset KEY`. Secrets are not readable after setting (write-only in the dashboard). Rotation: `fly secrets set KEY=new_value` followed by `fly deploy` (or `fly machines restart`) to apply to the running machine. Critical: `fly secrets set` alone does not restart the machine.
- **Rollback**: `fly releases` lists all prior deployments with image tags. Revert with `fly deploy --image registry.fly.io/<app>:<image-id>`. Typical time-to-revert: ~60–90 seconds (re-deploy of existing image, no rebuild). Caveat: database migrations applied in the broken deploy do not roll back automatically — backward-compatible migration discipline is required.
- **Approval**: An agent may run `fly deploy`, `fly secrets set`, `fly logs`, and `fly releases` unattended. Human approval required for: deleting the app (`fly destroy`), rotating the `FLY_API_TOKEN` itself, and any `fly postgres` or Supabase destructive operations. Database drops and secret rotation are panel-by-hand operations.
- **Logs**: `fly logs` streams live logs from the running machine. `fly logs --no-tail` prints recent lines and exits (useful for CI). Log retention is limited; for persistent log storage, pipe to an external service or use `fly logs > deploy.log` in CI.

## Risk Register

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Auto-stop default causes cold starts in production | Devil's advocate | High | Medium | Set `auto_stop_machines = false` and `min_machines_running = 1` in `fly.toml` immediately after `fly launch` |
| `fly secrets set` doesn't apply to running machine without restart | Unknown unknowns | High | Medium | Always follow `fly secrets set` with `fly deploy` or document the restart step in the deploy runbook |
| Custom Dockerfile required for uv (first-deploy friction) | Devil's advocate | High | Low | Write the Dockerfile before first deploy; use `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` as base |
| IPv4 allocation adds $2/month unexpectedly | Unknown unknowns | High | Low | Note the $2/month IPv4 cost in the budget; allocate a shared IPv4 explicitly and track it |
| Supabase free-tier project pauses after 1 week of inactivity | Unknown unknowns | Medium | High | Set up a lightweight uptime monitor (e.g., UptimeRobot free tier) to ping the app every 24h; or upgrade to Supabase Pro if the app is used in production |
| Migration failure leaves schema forward-migrated while old code runs | Pre-mortem | Low | High | Follow backward-compatible migration discipline: deploy schema changes separately from code changes; test migrations on staging before production |
| `release_command` migrate runs on every deploy including rollbacks | Research finding | Low | Medium | Ensure all migrations are backward-compatible; test rollback procedure on staging |
| No CLI rollback — incident response requires dashboard | Devil's advocate | Low | Medium | Document the `fly releases` + `fly deploy --image` rollback procedure; bookmark the Fly dashboard on mobile |
| OpenRouter API key not visible after `fly secrets set` without restart | Pre-mortem | Medium | Medium | Include `fly deploy` in the secrets-rotation runbook; never set secrets and assume they're live without verifying |
| Experimental MCP server unreliable for agent-driven operations | Devil's advocate | Medium | Low | Use `flyctl` CLI as the primary agent interface; treat MCP as supplementary until it reaches GA |

## Getting Started

1. **Install flyctl**: `curl -L https://fly.io/install.sh | sh` (Linux/macOS) or see [fly.io/docs/flyctl/install](https://fly.io/docs/flyctl/install/) for Windows. Authenticate: `fly auth login`.

2. **Write a uv-aware Dockerfile** (do not rely on `fly launch` auto-generation for uv projects):
   ```dockerfile
   FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
   WORKDIR /app
   COPY pyproject.toml uv.lock ./
   RUN uv sync --frozen --no-dev

   FROM python:3.12-slim-bookworm
   WORKDIR /app
   COPY --from=builder /app/.venv .venv
   COPY . .
   ENV PATH="/app/.venv/bin:$PATH"
   RUN python manage.py collectstatic --noinput
   CMD ["gunicorn", "korpotron.wsgi", "--bind", "0.0.0.0:8080"]
   ```

3. **Initialize the Fly app**: `fly launch --no-deploy` — this creates `fly.toml` without deploying. Immediately edit `fly.toml` to set:
   ```toml
   [http_service]
     auto_stop_machines = false
     min_machines_running = 1
   [deploy]
     release_command = "python manage.py migrate"
   ```

4. **Set required secrets before first deploy**:
   ```bash
   fly secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
   fly secrets set DATABASE_URL="postgresql://..."   # Supabase connection string
   fly secrets set OPENROUTER_API_KEY="sk-or-..."
   fly secrets set DJANGO_ALLOWED_HOSTS="korpotron.fly.dev"
   ```

5. **Deploy**: `fly deploy` — the `release_command` runs `manage.py migrate` before the new version starts. Verify with `fly logs` and `fly status`.

## Out of Scope

The following were not evaluated in this research:
- Docker image optimisation (layer caching, multi-stage size reduction)
- CI/CD pipeline configuration (GitHub Actions workflow for auto-deploy)
- Production-scale architecture (multi-region, HA, read replicas)
- Supabase connection pooling configuration (PgBouncer / Supavisor for high-concurrency workloads)
