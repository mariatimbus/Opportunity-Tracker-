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
8. **report** — per-source counters (fetched/accepted/created/updated/duplicates/
   rejected/failed) plus failed sources, rendered as text.

## Runner (A15)

The runner (`opportunity_api.ingestion.runner.IngestionRunner`) coordinates the
whole flow. It runs any number of adapters in sequence, isolates failures (a
crashing adapter never aborts the run), and returns an `IngestionReport`.

```python
from opportunity_api.ingestion.persistence import OpportunityStore
from opportunity_api.ingestion.runner import IngestionRunner
from opportunity_api.ingestion import registry

session = ...  # SQLAlchemy session against Supabase
store = OpportunityStore(session)

# Dry run: fetch → scope → normalize → dedupe → validate, no writes.
report = IngestionRunner(store, dry_run=True).run(registry.resolve())
print(report.render())

# Real run: same flow, then upsert + commit.
report = IngestionRunner(store).run(registry.resolve(["greenhouse", "lever"]))
print(report.render())
```

Example report output:

```text
Ingestion completed

greenhouse: fetched=150 accepted=90 created=20 updated=70 duplicates=0 rejected=60 failed=0
lever: fetched=120 accepted=75 created=15 updated=60 duplicates=0 rejected=45 failed=0

totals: fetched=270 accepted=165 created=35 updated=130 duplicates=0 rejected=105 failed=0
```

### Adding a new source (Dalia, C4)

Integration is one registration — no persistence, dedupe or reporting code:

```python
from opportunity_api.ingestion import registry
from opportunity_api.ingestion.sources.greenhouse import GreenhouseAdapter

registry.register(GreenhouseAdapter())
```

Selection by name (`registry.resolve(["greenhouse"])`) is what scheduled runs
(GitHub Actions) use to run all active sources or an explicit subset.

### Pipeline stages are injectable

The normalize/dedupe/validate stages belong to C3. Until they land, the runner
ships correct-but-simple defaults (`default_normalize`, pydantic validation,
DB-level dedupe via upsert). C3 replaces them without touching the runner:

```python
runner = IngestionRunner(
    store,
    normalizer=my_normalize,   # RawOpportunity -> NormalizedOpportunity fields
    validate=my_validate,      # final NormalizedOpportunity
    dedupe=my_dedupe,          # optional within-run duplicate detection
)
```

### Idempotency

Identity is `(source, source_id)` (or canonical `url` when no `source_id`
exists). Re-running the pipeline over the same data updates existing rows
instead of inserting duplicates — the runner tests assert this directly
(second run: `created=0, updated=N`, row count unchanged).
