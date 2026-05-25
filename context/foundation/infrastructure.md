---
project: korpotron
researched_at: 2026-05-25
recommended_platform: Fly.io
runner_up: Railway
context_type: mvp
tech_stack:
  language: Python 3.12
  framework: Django
  runtime: Gunicorn (WSGI)
  package_manager: uv
  database: Supabase (external PostgreSQL)
  llm_provider: OpenRouter (external API)
---

## Recommendation

**Deploy on Fly.io.**

Fly.io runs Django as a persistent micro-VM process — the same Gunicorn WSGI model that Django expects — with no serverless cold-start compromise. The `flyctl` CLI covers every routine operation without interactive prompts, the docs publish `llms.txt` for agent consumption, and Supabase as the external database means the most complex co-location concern is already solved before the platform is involved. Estimated cost is $5–10/month for a single always-on instance. The one setup cost vs. the runner-up is a custom Dockerfile (required because `fly launch` does not auto-detect uv), but this is a one-time investment that gives full control over the build environment.

## Platform Comparison

| Platform | CLI-first | Managed/Serverless | Agent-readable docs | Stable deploy API | MCP/Integration | Total |
|---|---|---|---|---|---|---|
| **Fly.io** | Pass | Partial | Pass | Pass | Partial | 3.5 |
| **Railway** | Pass | Pass | Partial | Pass | Pass | 4 |
| **Render** | Partial | Pass | Pass | Partial | Partial | 3 |
| Vercel | Pass | Pass | Pass | Pass | Pass | 5* |
| Netlify | — | Fail (hard filter) | Pass | Pass | Pass | dropped |
| Cloudflare Workers | — | Fail (hard filter) | Pass | Pass | Pass | dropped |

*Vercel scores 5/5 on generic criteria but falls to 4th on Django fit: serverless Fluid Compute reduces cold starts but does not guarantee persistent state, and the Hobby plan's 4 CPU-hr/month cap is the binding constraint for a Django app.

**Hard filters applied:**
- **Netlify**: serverless-only, no persistent WSGI process. Django via Lambda shims is fragile and community-unsupported. Dropped before scoring.
- **Cloudflare Workers**: Python runtime is open beta (not GA), Django support is entirely community-maintained (`django-cf`), V8 isolate model provides no persistent process, and `psycopg2` availability in Pyodide for Supabase connections is unconfirmed. Dropped before scoring.

### Shortlisted Platforms

#### 1. Fly.io (Recommended)

Fly.io runs applications on micro-VMs, not serverless lambdas — a Django/Gunicorn process stays alive between requests exactly as it would on a VPS. `flyctl` is comprehensive: `fly deploy`, `fly logs`, `fly secrets set`, and `fly releases` for rollback cover all routine operations non-interactively. The docs publish `llms.txt` and `flyctl` is open-source on GitHub. No free tier (deprecated), but a minimal always-on instance costs ~$5–10/month including shared IPv4. The MCP server (`fly mcp server`) exists but is marked experimental. The one setup gap for this stack: `fly launch` does not auto-detect uv; a custom multi-stage Dockerfile using the official `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` base image is required.

#### 2. Railway

Railway's Nixpacks builder auto-detects `uv.lock` and invokes `uv sync --no-dev --frozen` with no Dockerfile required — the smoothest first-deploy path for this exact stack. The official MCP server is GA and integrates directly with Claude Code (`claude mcp add railway-mcp-server -- npx -y @railway/mcp-server`). Hobby plan is $5/month. The key gap: there is no CLI rollback — reverting to a prior deployment requires the dashboard. The GitHub-hosted markdown docs are agent-readable but no `llms.txt` was confirmed published.

#### 3. Render

Render added native uv support to its Python runtime in June 2025 (GA): it auto-detects `uv.lock` and runs `uv sync --no-dev` with no Dockerfile. Starter web service is $7/month (always-on, 512 MB RAM). Publishes `llms.txt` and `llms-full.txt`. Official MCP server (GA August 2025) exposes 20+ tools, but cannot trigger deploys — deploy triggering requires a separate CLI path. The free tier is available but spins down after 15 minutes of inactivity (~60-second cold start), making it suitable for testing only.

## Anti-Bias Cross-Check: Fly.io

### Devil's Advocate — Weaknesses

1. **No free tier.** The Hobby plan was deprecated. A minimal always-on instance (shared-cpu-1x 512 MB + shared IPv4) costs ~$6/month from day one, with no grace period beyond the initial 2-VM-hour trial.
2. **uv is not auto-detected by `fly launch`.** The generated Dockerfile uses pip/requirements.txt conventions. A custom multi-stage Dockerfile is required before first deploy, adding 30–60 minutes of setup cost Railway eliminates entirely.
3. **Auto-stop default causes production cold starts.** `fly launch` generates `auto_stop_machines = "stop"` — the VM spins down after idle and takes several seconds to restart. Overriding to `min_machines_running = 1` / `auto_stop_machines = false` is required but not obvious from defaults.
4. **Rollback is not a first-class CLI command.** There is no `fly rollback`. Reverting requires identifying the previous image tag via `fly releases` and running `fly deploy --image registry.fly.io/<app>:<tag>` — more friction than a single command.
5. **MCP server is experimental.** `fly mcp server` carries an explicit `[experimental]` label. Agent-driven operations fall back to plain CLI, losing structured-tool ergonomics.

### Pre-Mortem — How This Could Fail

The team deployed korpotron to Fly.io. Six months later, the platform was a persistent source of friction. First deploy required a hand-written Dockerfile because `fly launch` generated a pip-based image that missed the `uv` lockfile — a community forum post found the fix after an hour. The auto-stop default wasn't caught in review; the first real user hit a 6-second cold start and the developer didn't notice for a week because local dev never cold-starts. After disabling auto-stop, the always-on machine plus shared IPv4 came to $8/month instead of the mentally-budgeted $5. When OpenRouter integration shipped, `fly secrets set OPENROUTER_API_KEY=...` worked but the running machine didn't pick up the new var until a manual restart — a half-day of "why is the API key missing?" A migration failure mid-deploy left the database in a forward-migrated state while the old container kept serving traffic, producing 20 minutes of 500 errors requiring an emergency redeploy. When an agent tried to instrument the platform via the MCP server, the experimental flag produced inconsistent results and the fallback CLI approach required ambient auth context the agent didn't have in CI.

### Unknown Unknowns

- **IPv4 is $2/month and allocated by default.** Fly assigns a shared IPv4 automatically; IPv6 is free but not universally supported. Most new users are surprised when the "tiny app" costs $2 more than the VM price suggests.
- **`fly secrets set` does not restart the running machine.** The new env var is not visible to the live process until `fly deploy` or an explicit machine restart. The CLI gives no warning about this.
- **`fly launch` uv detection gap is known in the community but not prominent in official docs.** The recommended path — a custom Dockerfile from the uv base image — requires a community forum thread to discover.
- **`release_command` migrations carry a partial-failure risk.** If a migration fails mid-deploy, Fly aborts starting the new version but the schema change may already be applied. The old container continues running against a forward-migrated schema, which can cause errors if the old code is incompatible.
- **Wireguard required for some local→Fly resource access.** `fly ssh console` and certain proxy operations require the Fly Wireguard tunnel. Not a concern for Supabase-backed deploys, but surprising for developers who expect plain TCP access.

## Operational Story

- **Preview deploys**: No automatic PR preview URL out of the box. Branch deploys can be configured by creating a second Fly app (e.g., `korpotron-staging`) and deploying to it from CI on a feature branch. Fly offers no automatic per-PR preview environment like Vercel. For MVP, a single production app is sufficient.
- **Secrets**: All env vars and tokens are set via `fly secrets set KEY=value`. Secrets are encrypted at rest and injected into the container as env vars at boot. They are not visible in `fly.toml` or the container image. Rotation: `fly secrets set KEY=new_value` followed by `fly deploy` (or `fly machines restart` for immediate pickup without a full deploy).
- **Rollback**: No `fly rollback` command. Steps: (1) `fly releases` to list image tags, (2) `fly deploy --image registry.fly.io/<app>:<tag>` to redeploy a prior version. Typical time-to-revert: 2–4 minutes including image pull. Data caveat: DB migrations run via `release_command` do not automatically roll back — schema must be manually reverted if the migration was destructive.
- **Approval**: Human-only actions: deleting the app, rotating the `SECRET_KEY` (requires updating Supabase sessions too), increasing machine count or size beyond the current tier. Agent-permissible unattended: `fly deploy`, `fly secrets set`, `fly logs`, `fly releases`, `fly scale`.
- **Logs**: `fly logs` (streaming, follows new lines). `fly logs --no-tail` for a snapshot. `fly logs -i <machine-id>` for a specific machine. No retention limit noted for the CLI stream; dashboard log retention is 30 days.

## Risk Register

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Auto-stop cold starts in production | Devil's advocate | H | M | Set `auto_stop_machines = false` and `min_machines_running = 1` in `fly.toml` before first production deploy |
| IPv4 surprise cost ($2/month) | Unknown unknowns | H | L | Budget for $2/month shared IPv4 from the start; document it in ops notes |
| `fly secrets set` not picked up by running machine | Unknown unknowns | M | M | Always follow `fly secrets set` with `fly deploy` or `fly machines restart`; add to ops runbook |
| Custom Dockerfile setup cost (uv not auto-detected) | Devil's advocate | H | L | Write Dockerfile once using `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`; commit and done |
| Migration partial-failure leaves schema ahead of code | Pre-mortem | L | H | Use backward-compatible migrations (add column first, deploy, then drop old column in v2); never deploy destructive migration and new code in the same release |
| Experimental MCP server unreliability | Devil's advocate | M | L | Use `flyctl` CLI directly for agent operations; treat MCP as supplemental when stable |
| `SECRET_KEY` scaffold default in production | Research finding | H | H | `fly secrets set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")` before first production deploy |
| OpenRouter API key not propagating to live container | Pre-mortem | M | M | After setting any new secret, always trigger a deploy or machine restart; verify with `fly secrets list` |

## Getting Started

1. **Install flyctl**: `curl -L https://fly.io/install.sh | sh` — or via Homebrew: `brew install flyctl`. Authenticate: `fly auth login`.
2. **Write the uv Dockerfile**: Create a `Dockerfile` in the project root using the official uv base image (do not use `fly launch` auto-generation for uv projects):
   ```dockerfile
   FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
   WORKDIR /app
   COPY pyproject.toml uv.lock ./
   RUN uv sync --frozen --no-dev

   FROM python:3.12-slim-bookworm
   WORKDIR /app
   COPY --from=builder /app/.venv /app/.venv
   COPY . .
   ENV PATH="/app/.venv/bin:$PATH"
   CMD ["gunicorn", "korpotron.wsgi", "--bind", "0.0.0.0:8080"]
   ```
3. **Initialise the Fly app**: `fly launch --no-deploy` — review and edit the generated `fly.toml`. Override the auto-stop default:
   ```toml
   [http_service]
     auto_stop_machines = false
     min_machines_running = 1
   
   [deploy]
     release_command = "python manage.py migrate"
   ```
4. **Set required secrets** before first deploy:
   ```
   fly secrets set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
   fly secrets set DATABASE_URL=<your-supabase-connection-string>
   fly secrets set OPENROUTER_API_KEY=<your-openrouter-key>
   fly secrets set DJANGO_SETTINGS_MODULE=korpotron.settings
   ```
5. **Deploy**: `fly deploy` — this builds the image, runs the `release_command` (migrate), and starts the machine. Verify with `fly logs` and `fly status`.

## Out of Scope

The following were not evaluated in this research:
- Docker image optimisation (layer caching, multi-stage build tuning)
- CI/CD pipeline setup (GitHub Actions auto-deploy workflow)
- Production-scale architecture (multi-region, HA, DR)
- Media file storage configuration (S3/R2 for user uploads)
- Email delivery setup (transactional email provider)
