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
- `database/` — migrations and seeds

## Quickstart

1. Clone the repo.
2. `cp .env.example .env` and fill in values.
3. Start the database: `docker compose up db`
4. Backend: see `apps/api/README.md` (uses `uv` + Python 3.13).

See `docs/architecture.md` for structure and `docs/contributing.md` for workflow.
