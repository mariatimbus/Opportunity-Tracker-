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
  without Postgres. Use `postgresql+psycopg://...` for the docker-compose db.
- `CORS_ORIGINS` — comma-separated allowed origins

## Endpoints

- `GET /health` — liveness, returns `{"status": "ok"}`
- `GET /health/db` — database connectivity check, 503 on failure

OpenAPI docs at `/docs` when the server is running.
