# Opportunity ingestion

The C2 manual importer is `opportunity_api.ingestion.seed` in the existing backend
Python package, reusing its reviewed enums and database dependencies. From the root:

```powershell
uv run --project apps/api python -m opportunity_api.ingestion.seed
```

Default behavior is offline validation only. See
[the audited seed guide](../../database/seeds/README.md) for generation, deterministic
IDs, atomic upserts, rejection reports and the explicit `--apply` approval gate.
Do not run hosted imports or publish candidates without Dalia's approval.

## Pipeline (A14 ingestion contract)

Every automated source flows through the same stages:

```text
source adapter → RawOpportunity → scope → normalize → dedupe → validate → persistence
```

1. **source adapter** — a `SourceAdapter` implementation in
   `opportunity_api.ingestion.sources` (Greenhouse, Lever, SmartRecruiters, ...).
   Adapters must be idempotent: re-runs yield the same `source_id`/`source_url`.
2. **RawOpportunity** — the un-normalized contract in
   `opportunity_api.ingestion.models`. Fields the source did not provide stay
   `None`; a record needs at least one of `source_id` / `source_url`.
3. **scope** — `opportunity_api.ingestion.scope.assess_scope` keeps only
   internship-level student roles (intern / working student / Werkstudent /
   placement / student worker) that are tech/STEM and located in Europe
   (or remote). Everything else is dropped before any further work.
4. **normalize** — parse `deadline_raw`, `degree_level_raw`, `study_year_raw`
   into typed values against the final enums.
5. **dedupe** — drop records already known by `(source, source_id)` or canonical URL.
6. **validate** — enforce the persistence schema and API contract.
7. **persistence** — upsert into Supabase; repeated runs must not create duplicates.

The A15 runner orchestrates adapters and stages; until it lands, run the stages
explicitly per adapter.
