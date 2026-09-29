# ORCA — Render + Cloudflare Workers Deployment Guide

> **This guide is based on direct code inspection and actual build tests.**
> Deploy services in the exact order listed in the Deployment Order section.

---

## Prerequisites

- GitHub repository with the ORCA code pushed (including large data files via Git LFS)
- Render account connected to the GitHub repository
- Cloudflare account with Wrangler CLI (`npx wrangler`)
- Gemini API key

---

## PostgreSQL Setup

1. In Render Dashboard → **New** → **PostgreSQL**
2. Settings: Name = `orca-db`, same Region as your backend services
3. After creation, you will have two URLs:
   - **Internal Database URL** — use this inside Render services (same region, no egress fees)
   - **External Database URL** — use this for migrations run from your local machine
4. ORCA automatically normalises `postgres://` → `postgresql://` for SQLAlchemy compatibility.

### Run Migrations (from your local machine after orca-auth is deployed)

Run **from the project root** (where `alembic.ini` lives):

```bash
export DATABASE_URL="postgres://user:password@host:5432/dbname"   # External URL
alembic upgrade head
```

> On Windows PowerShell:
> ```powershell
> $env:DATABASE_URL="postgres://user:password@host:5432/dbname"
> alembic upgrade head
> ```

Alembic reads `backend/auth/alembic/` as its script location (configured in `alembic.ini`).
`env.py` adds the project root to `sys.path` automatically, so `backend.*` imports resolve.

Two migrations will run:
- `0001_create_users` — users table
- `0002_create_vessels` — vessels table (FK to users)

---

## Backend Services (Render)

All **6** backend services use these Render settings:

| Setting | Value |
|---------|-------|
| Runtime | Python 3 |
| Root Directory | `.` (project root — **NOT** `backend/`) |
| Build Command | `pip install -r backend/requirements.txt` |

> **CRITICAL**: All services MUST start from the project root so that
> `backend.*` Python package imports resolve correctly.
> This was verified by actually importing all six apps.

---

### 1. Auth Service

| Setting | Value |
|---------|-------|
| Service Name | `orca-auth` |
| Start Command | `uvicorn backend.auth.main:app --host 0.0.0.0 --port $PORT` |
| Health Endpoint | `GET /health` |

Environment Variables:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Render PostgreSQL **Internal** URL (same region) |
| `JWT_SECRET` | Strong random secret (min 32 chars) |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_EXPIRATION_MINUTES` | `1440` |
| `FRONTEND_URL` | Your Cloudflare Workers URL (e.g. `https://orca.your-subdomain.workers.dev`) |

---

### 2. Ocean Agent

| Setting | Value |
|---------|-------|
| Service Name | `orca-ocean` |
| Start Command | `uvicorn backend.api.ocean_api:app --host 0.0.0.0 --port $PORT` |
| Health Endpoint | `GET /health` |

Environment Variables:

| Variable | Value |
|----------|-------|
| `FRONTEND_URL` | Your Cloudflare Workers URL |
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` |

---

### 3. Safety Agent

| Setting | Value |
|---------|-------|
| Service Name | `orca-safety` |
| Start Command | `uvicorn backend.api.safety_api:app --host 0.0.0.0 --port $PORT` |
| Health Endpoint | `GET /health` |

Environment Variables:

| Variable | Value |
|----------|-------|
| `FRONTEND_URL` | Your Cloudflare Workers URL |
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` |

---

### 4. Route Agent

| Setting | Value |
|---------|-------|
| Service Name | `orca-route` |
| Start Command | `uvicorn backend.api.route_api:app --host 0.0.0.0 --port $PORT` |
| Health Endpoint | `GET /health` |

Environment Variables:

| Variable | Value |
|----------|-------|
| `FRONTEND_URL` | Your Cloudflare Workers URL |

---

### 5. Decision Layer

| Setting | Value |
|---------|-------|
| Service Name | `orca-decision` |
| Start Command | `uvicorn backend.agents.decision_layer.main:app --host 0.0.0.0 --port $PORT` |
| Health Endpoint | `GET /health` |

Environment Variables:

| Variable | Value |
|----------|-------|
| `FRONTEND_URL` | Your Cloudflare Workers URL |

---

### 6. Query Agent *(deploy last among backends)*

This is the primary service the frontend communicates with.
It proxies to all other agents and handles auth token verification.

| Setting | Value |
|---------|-------|
| Service Name | `orca-query` |
| Start Command | `uvicorn backend.agents.query_agent.main:app --host 0.0.0.0 --port $PORT` |
| Health Endpoint | `GET /health` |

Environment Variables:

| Variable | Value |
|----------|-------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` |
| `FRONTEND_URL` | Your Cloudflare Workers URL |
| `OCEAN_API` | Public Render URL of orca-ocean (e.g. `https://orca-ocean.onrender.com`) |
| `SAFETY_API` | Public Render URL of orca-safety |
| `ROUTE_API` | Public Render URL of orca-route |
| `DECISION_API` | Public Render URL of orca-decision |
| `DATABASE_URL` | Render PostgreSQL **Internal** URL (same region) |
| `JWT_SECRET` | Same secret as Auth service |
| `JWT_ALGORITHM` | `HS256` |

> **Internal vs External DATABASE_URL**: Use the Render **Internal** URL for both
> `orca-auth` and `orca-query` when they run in the same Render region. The Internal
> URL is faster and does not incur egress fees. Only use the External URL for running
> Alembic from your local machine.

---

## Frontend (Cloudflare Workers)

The ORCA frontend uses **TanStack Start** with a **Cloudflare Workers** build target
via Nitro preset `cloudflare-module`. It is deployed as a **Cloudflare Worker** —
**NOT** Cloudflare Pages and **NOT** a static site.

### Build

```bash
cd frontend
npm install
npm run build
```

Build command: `npm run build` (wraps `vite build`)

**Verified build output** (exit code 0, tested 2026-09-29):

| Path | Purpose |
|------|---------|
| `.output/server/index.mjs` | Cloudflare Worker entry point |
| `.output/server/wrangler.json` | Auto-generated Wrangler config |
| `.output/public/` | Static assets (served by the Worker via ASSETS binding) |

The Wrangler config (`.output/server/wrangler.json`) is auto-generated by Nitro
with `"main": "index.mjs"` and `"assets": { "binding": "ASSETS", "directory": "../public" }`.

### Deploy with Wrangler

```bash
cd frontend
npx wrangler deploy --config .output/server/wrangler.json
```

Or use the Nitro deploy shorthand from inside `.output/`:

```bash
npx nitro deploy --prebuilt
```

Wrangler will:
1. Upload `.output/server/index.mjs` as the Worker script
2. Upload `.output/public/` as static assets

### Environment Variables for the Worker

> **IMPORTANT**: TanStack Start bakes `VITE_*` variables into the client bundle at
> build time (via Vite's `import.meta.env`). You must rebuild after changing these values.
> Set them in `frontend/.env` **before** running `npm run build`.

Create `frontend/.env` with:

```
VITE_API_BASE_URL=https://orca-query.onrender.com
VITE_AUTH_API_URL=https://orca-auth.onrender.com
```

### Cloudflare Pages vs Cloudflare Workers

| | This project |
|-|---|
| Deployment type | **Cloudflare Workers** |
| Config file | `.output/server/wrangler.json` (auto-generated) |
| Deploy command | `npx wrangler deploy --config .output/server/wrangler.json` |
| Static assets | Served by the Worker via ASSETS binding |
| SSR | Yes — Nitro Worker handles SSR |

Do **not** use Cloudflare Pages for this project. The Nitro build target is
`cloudflare-module` (a Cloudflare Worker), not `cloudflare-pages`.
Do **not** set `.output/public` as the "output directory" in any Cloudflare Pages
settings — that would only serve static assets without the Worker/SSR layer.

---

## Environment Variables Reference

### Backend

| Variable | Used By | Purpose | Example |
|----------|---------|---------|---------|
| `GEMINI_API_KEY` | query, ocean, safety | Google Gemini API key | `your_gemini_api_key_here` |
| `GEMINI_MODEL` | query, ocean, safety | Gemini model name | `gemini-2.5-flash-lite` |
| `DATABASE_URL` | auth, query | PostgreSQL connection URL | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET` | auth, query | JWT signing secret (32+ chars) | `your_strong_jwt_secret_here` |
| `JWT_ALGORITHM` | auth, query | JWT algorithm | `HS256` |
| `JWT_EXPIRATION_MINUTES` | auth | Token TTL in minutes | `1440` |
| `FRONTEND_URL` | all backend | CORS allowed origin | `https://orca.your-subdomain.workers.dev` |
| `OCEAN_API` | query | Ocean Agent URL | `https://orca-ocean.onrender.com` |
| `SAFETY_API` | query | Safety Agent URL | `https://orca-safety.onrender.com` |
| `ROUTE_API` | query | Route Agent URL | `https://orca-route.onrender.com` |
| `DECISION_API` | query | Decision Layer URL | `https://orca-decision.onrender.com` |

### Frontend (baked into the bundle at build time)

| Variable | Purpose | Example |
|----------|---------|---------|
| `VITE_API_BASE_URL` | Query Agent public URL | `https://orca-query.onrender.com` |
| `VITE_AUTH_API_URL` | Auth Agent public URL | `https://orca-auth.onrender.com` |

---

## Deployment Order

```
1. PostgreSQL database      (Render managed database — create first)
2. orca-auth               (depends on: PostgreSQL)
   → run alembic upgrade head from project root with External DATABASE_URL
3. orca-ocean              (no inter-service dependencies)
4. orca-safety             (no inter-service dependencies)
5. orca-route              (no inter-service dependencies)
6. orca-decision           (no inter-service dependencies)
7. orca-query              (depends on: ocean, safety, route, decision, PostgreSQL)
   → set OCEAN_API, SAFETY_API, ROUTE_API, DECISION_API from steps 3-6
8. orca-frontend           (Cloudflare Worker — depends on: orca-query, orca-auth)
   → set VITE_API_BASE_URL, VITE_AUTH_API_URL in frontend/.env
   → run: cd frontend && npm run build
   → run: npx wrangler deploy --config .output/server/wrangler.json
   → then set FRONTEND_URL = Cloudflare Workers URL in ALL Render services (steps 2-7)
   → redeploy all Render services so CORS accepts the Workers URL
```

---

## Post-Deployment Testing

```bash
# All should return: {"status": "ok"}
curl https://orca-auth.onrender.com/health
curl https://orca-ocean.onrender.com/health
curl https://orca-safety.onrender.com/health
curl https://orca-route.onrender.com/health
curl https://orca-decision.onrender.com/health
curl https://orca-query.onrender.com/health
```

Then open your Cloudflare Workers URL and verify:
1. Dashboard loads without errors
2. Login / registration works
3. The ORCA assistant responds to a query
4. Ocean conditions panel loads data
5. Safety alerts panel loads data
6. Map renders correctly
7. Voice input (transcribe / synthesize) works
8. Route navigation (A* map) works

---

## Git LFS — Large Data Files

Files tracked by Git LFS (configured in `.gitattributes`):

| File | Disk size | LFS object size | Purpose |
|------|-----------|-----------------|---------|
| `backend/data/routing/grid/orca_west_coast_bathymetry_landmasked.nc` | 101.82 MB | 107 MB | Bathymetry grid for A* navigation |
| `backend/data/routing/environmental/orca_west_coast_currents_departure.nc` | 133.13 MB | 140 MB | Ocean currents for route cost |

**Status (verified 2026-09-29)**: Both files are **actual NetCDF files** in the working tree
(not LFS pointer text files). They are correctly tracked by Git LFS.

### Before Deploying

```bash
git lfs install
git lfs ls-files          # Both .nc files must appear with asterisk (*)
git push origin main      # Pushes LFS objects automatically
```

Render downloads Git LFS files during build automatically — no special config needed.

If navigation fails on Render with file-not-found errors, re-push LFS objects:

```bash
git lfs push --all origin main
```

> **Note**: Safety, ocean conditions, fishing zones, and the AI assistant all work
> WITHOUT the .nc files. Only the A* map navigation depends on them.

---

## Alembic — Verified Configuration

| Item | Value |
|------|-------|
| Config file | `alembic.ini` (project root) |
| Script location | `backend/auth/alembic/` |
| Run from | Project root |
| Command | `alembic upgrade head` |
| DATABASE_URL | Must be set in environment before running (use External URL) |

`env.py` automatically adds the project root to `sys.path` so `backend.*` imports work.
Both `alembic.ini` and the two migration files (`0001_create_users`, `0002_create_vessels`)
were verified to be present and correctly configured.

---

## Local Development

The existing `START_ORCA.bat` is unchanged. No modifications needed for local dev.

```bat
START_ORCA.bat
```

Environment variables are loaded from the root `.env` file.
All services start on their fixed local ports (8000-8005).
