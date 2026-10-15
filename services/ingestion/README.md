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
