# apps/api

FastAPI backend for the Opportunity Tracker platform.

## Setup

Uses [uv](https://docs.astral.sh/uv/) with Python 3.13.

```bash
uv sync                  # create .venv and install deps (lockfile committed)
uv run pytest            # run tests
uv run ruff check .      # lint
uv run uvicorn opportunity_api.main:create_app --factory --reload
```

## Configuration

Environment variables (see `.env.example` at the repo root):

- `APP_NAME` — application name (default `opportunity-api`)
- `DEBUG` — debug mode (default `false`)
- `DATABASE_URL` — SQLAlchemy URL; defaults to a local sqlite file so the app boots
  without Postgres. Point it at your Supabase Postgres for real data.
- `CORS_ORIGINS` — comma-separated allowed origins
- `APP_SUPABASE_URL` — your Supabase project URL
- `APP_SUPABASE_JWT_SECRET` — optional legacy HS256 secret; leave empty for ES256/RS256 (project JWKS is used)
- `APP_SUPABASE_JWT_AUDIENCE` — JWT audience to validate (default `authenticated`)
- `APP_RATE_LIMIT_PER_MINUTE` — per-client-IP request limit per minute (default
  `240`); `0` or negative disables rate limiting

## Auth

Sign-up and sign-in happen client-side against Supabase Auth. The backend only
validates Supabase-issued JWT access tokens (sent as `Authorization: Bearer ...`)
and uses the shared Supabase PostgreSQL domain tables. Auth triggers create identity/profile rows; the first-request fallback remains for offline tests.
Use a Supabase access token in the `/docs` Authorize dialog.

## Endpoints

- `GET /health` — liveness, returns `{"status": "ok"}`
- `GET /health/db` — database connectivity check, 503 on failure

OpenAPI docs at `/docs` when the server is running.

## Shared database

See [the team setup guide](../../supabase/README.md). Use the hosted connection for team development and run commands from the repository root with `uv run --project apps/api ...` so the root `.env` is loaded. Alembic is historical; apply schema changes through committed Supabase SQL migrations.
