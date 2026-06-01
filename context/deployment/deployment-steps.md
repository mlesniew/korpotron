# Deployment Steps

All code changes (Dockerfile, settings, fly.toml, GitHub Actions workflow) are already in the repo. These are the manual steps needed to wire up a fresh deployment.

---

## 1. Prerequisites

### Fly.io

```bash
curl -L https://fly.io/install.sh | sh   # installs to ~/.fly/bin/
fly auth login
fly apps create korpotron --org personal
```

If `korpotron` is taken, pick a variant and update `app =` in `fly.toml`.

### Supabase

Create a project at supabase.com — use the **Frankfurt (eu-central-1)** region for lowest latency from the Amsterdam Fly.io machine.

Grab the connection string: Settings → Database → Connection string → URI tab → **Transaction pooler** (port 6543):

```
postgresql://postgres.PROJECTREF:PASSWORD@HOST:6543/postgres?sslmode=require
```

### GitHub

Push `master` to GitHub (required for GitHub Actions).

---

## 2. Set Fly secrets

```bash
fly secrets set SECRET_KEY="$(python -c "import secrets; print(secrets.token_urlsafe(50))")"
fly secrets set DATABASE_URL="postgresql://..."   # from Supabase above
fly secrets set OPENROUTER_API_KEY="sk-or-v1-..."  # from openrouter.ai → Keys
```

`DJANGO_SETTINGS_MODULE` and `ALLOWED_HOSTS` are not needed — they're handled in the Dockerfile and derived from `FLY_APP_NAME` respectively.

`OPENROUTER_MODEL` and `OPENROUTER_BASE_URL` are optional (defaults: `openai/gpt-4o-mini` and `https://openrouter.ai/api/v1`). Set them only to override.

> **Note:** Setting a secret on an already-running app does not take effect until a redeploy or machine restart (`fly deploy` or `fly machine restart <id>`). Verify propagation with `fly secrets list`.

---

## 3. Deploy

```bash
fly deploy
```

The release command (`python manage.py migrate`) runs first; the deploy aborts if migrations fail. Watch with `fly logs`.

---

## 4. Create superuser

Machines may be stopped when idle. Start one if needed:

```bash
fly machine start <machine-id>   # get ID from: fly status
```

Then SSH in and create the superuser:

```bash
fly ssh console -a korpotron
python manage.py createsuperuser
```

---

## 5. Wire up GitHub Actions (one-time)

```bash
fly tokens create deploy -a korpotron
```

Add the token as a secret named `FLY_API_TOKEN` in the GitHub repo:
Settings → Secrets and variables → Actions → New repository secret.

After this, every push to `master` triggers an automatic deploy.

---

## Verification

- `https://korpotron.fly.dev/admin/` renders the login page (static files via WhiteNoise)
- Login succeeds without CSRF errors
- `fly logs` shows Gunicorn running with no errors
