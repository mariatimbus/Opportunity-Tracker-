# Opportunity Tracker

A Student Opportunity Intelligence Platform: one place to discover, track, and manage
internships, jobs, scholarships, hackathons, and grants.

## Overview

This repository is a monorepo:

- `apps/web` — Next.js frontend
- `apps/api` — FastAPI backend
- `services/ai` — AI services (Ollama adapters)
- `services/ingestion` — opportunity ingestion services
- `packages/` — shared packages (types, config)
- `supabase/` — versioned SQL migrations, RLS tests and shared development setup
- `database/` — legacy Alembic references and seed fixtures

## Quickstart

1. Clone the repo.
2. `cp .env.example .env` and configure the shared Supabase project URL and hosted database connection. ES256 Auth uses public JWKS; no JWT secret is required.
3. Backend: see `apps/api/README.md` (uses `uv` + Python 3.13).

See `docs/architecture.md` for structure and `docs/contributing.md` for workflow.

## Shared database setup

Follow [the Supabase team guide](supabase/README.md) to connect to the shared development project, apply committed migrations and run RLS tests. Normal team development uses the shared hosted Supabase project.
