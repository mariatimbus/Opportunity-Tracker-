# C2 repeatable opportunity seed

Status: local implementation validated; minimum-40/source approval gate is NOT satisfied.
Use the existing task branch `feature/dalia-supabase-seed`, whose base matches origin/develop.
All earlier uncommitted work is retained. No new tables, enums, migrations or API contracts.

The canonical input is `database/seeds/opportunities_seed.json`. `eligibility_audit.json`
records academic evidence; `source_verification.json` records current listing/content checks.
These are distinct from historical workbook verdicts and human publication approval.
`supabase/seed.sql` is a generated INACTIVE CANDIDATE artifact, not an approved public seed.
Current per-record review: [SOURCE_VERIFICATION.md](SOURCE_VERIFICATION.md).

## Actual dataset and verification counts

- 50 source records; all parse and match evidence fingerprints.
- 25 currently supported listing/programme records; 25 flagged or insufficiently verified.
- All 9 `Individual verification required` records explicitly flagged in the source ledger.
- Academic evidence separately: 38 confirmed, 12 unknown; this is not a live availability count.
- 0 publication-approved records; 0 records imported to shared Supabase by C2.
- 50 inactive rows imported into temporary PGlite; second import still 50, IDs/timestamps stable.
- Minimum 40 genuine verified opportunities: FAIL (25/40). No rows relabeled to pad the count.

A programme can be verified as announced but not yet open. An opportunity's verified facts
never imply every student is eligible. Unknown degree/year/country/skills remain unknown.
Closed/stale/generic/JS-only pages, conflated locations and conflicting dates are not counted.
Only verified source entries with `eligible_for_import=true` count toward the threshold.

## Reproduce locally, without a hosted database connection

Prerequisites: Node.js 20+, uv and a supported Python >=3.13. From repository root:

```powershell
npm ci
uv sync --project apps/api
npm run db:seed:dry-run
npm run db:seed:generate
npm run db:test:fresh
npm run db:test:seed
uv run --project apps/api pytest
uv run --project apps/api ruff check apps/api scripts/validate_c2_seed.py
npm run db:seed:check
```

`db:seed:check` currently exits 1 with `minimum not met: 25/40 current verified records`.
That is an acceptance failure, not a passing test. Technical tests pass independently.
Generation is deterministic; an automated test compares the SQL artifact to the generator.
Rejected rows prevent generation/application; DB errors roll back all writes.

## Fresh hosted project — ONLY after target/seed approval

Do not execute the following against shared resources before Dalia approves. First finish
source review so >=40 genuine records exist, then obtain explicit publication and target
approval. Do not convert workbook VERIFIED into approval. A reviewer must update the dataset's
`ready_for_public_seed`, `current_source_review=verified`, the current-source ledger's
`publication_approved`, and both evidence fingerprints after verifying the actual record.
Only rows passing BOTH review/publication gates are selected by the standard seed command.

```powershell
npx.cmd supabase login
npx.cmd supabase link --project-ref <approved-fresh-project-ref>
npx.cmd supabase db push --dry-run
npx.cmd supabase db push
# Set DATABASE_URL privately to the approved SQLAlchemy psycopg connection; SSL required.
npm run db:seed
npm run db:seed
```

`db:seed` validates first, requires 40 verified source records and selects only approved rows.
It refuses to connect when validation/minimum/publication gates fail. It uses the existing
psycopg/SQLAlchemy backend dependencies, no dashboard pasting. The pinned CLI (2.121.0)
supports `db query --linked --file`; after approval an approved-only SQL artifact can instead
be generated with the importer `--approved-only --require-minimum 40 --sql-output <file>`
and executed via that CLI. Do not use `db push --include-seed`: the default artifact contains
inactive candidates. Do not expose DB passwords, personal tokens or privileged keys.

For explicitly approved inactive preview imports only, the importer also supports
`--apply --include-inactive-candidates`; this is not the public seed command or proof of C2 done.

## Mapping, identity and corrections

The JSON's type -> opportunity_type, source_url -> url, nullable degree_level/study_year ->
existing enum/JSONB. released_date -> posted_at only if recorded, never date_checked.
Date-only deadlines use UTC midnight as a documented storage convention, not an invented
official deadline timezone/instant. Contradictory exact deadlines are flagged for review.
No inferred skill, degree, publication date or study year is filled in.

`source` remains the reconciled workbook/supplemental origin. The research source_id is the
24-hex canonical URL hash. Where the current official evidence provides a genuine ID, the
DB import uses that provider ID (for example amazon:10555873 or arm:2026-18044), otherwise
the stable research URL hash. Eleven corroborated provider IDs are recorded in the current
ledger; they are not guessed from titles. The earlier native/canonical key and the previous
reviewed hash key can each be adopted only when source identity AND exact URL match. UUIDs
are never replaced; application FKs remain valid. External feed URL conflicts fail/rollback.
Use these explicit reconciliation steps for legitimate corrections; changing an input without
review/fingerprint refresh is rejected. No-op upserts do not refresh opportunity timestamps.

Only confirmed mandatory skills populate skill links; unknown/empty means not recorded.
Provenance stays in JSON/ledgers and does not create schema columns. `description` carries
academic notes plus separately labeled historical research text. Approved open/rolling
entries can be active; announced entries stay inactive. Unverified candidates never activate.
Any exact source/timing/identity correction must be reviewed rather than inferred.

## Bianca: query approved active opportunities

Use the existing shared project URL and browser-safe publishable key, through the frontend's
Supabase client. Never use a service-role key or DATABASE_URL in browser code.

```javascript
const { data, error } = await supabase
  .from('opportunities')
  .select('id,title,organization,opportunity_type,url,degree_level,study_year,deadline,is_active')
  .eq('is_active', true)
  .order('title');
```

Equivalent SQL:

```sql
SELECT id, title, organization, url, degree_level, study_year
FROM public.opportunities
WHERE is_active = true
ORDER BY title;
```

The existing RLS/GRANT policies permit catalog SELECT for anon/authenticated. PGlite tests
exercise anon reads: current candidate seed returns 0 active records; a clearly synthetic
local approval fixture returns 1, proving permissions without claiming a hosted/browser test.
The API GET /api/v1/opportunities?is_active=true also uses the existing contract. Null eligibility
is not unrestricted eligibility; preserve the conditional notes and don't filter by old groups.

## Remaining blockers and review

25 < 40; resolve 25 flagged source cases or obtain approved replacement source records.
Do not add invented records. Full reasons/official links are in SOURCE_VERIFICATION.md/json.
Several sources are JS-only/unavailable, programme pages do not identify a specific call,
ETH/Saarland describe 2026, and some local descriptions conflate dates/locations.
Maria must review complex academic-year representation and the UTC date-only convention.
Shared application and Bianca's actual browser verification await explicit approval/access.

## Frontend handoff details

## Existing API contract (unchanged)

Use `GET /api/v1/opportunities` and `GET /api/v1/opportunities/{id}`. Use
`opportunity_type` in requests/responses, not the research JSON's `type`.
Responses include `id`, `source`, `source_id`, title/description/organization/location,
url, deadline, posted_at, is_active, degree_level, study_year and skills.
`degree_level` is `bachelor`, `master`, `both` or null. A bachelor/master filter includes
`both`; null rows do not match a degree filter. `study_year=2` uses exact membership;
null rows do not match. Unknown rows still appear in the unfiltered catalog.

`study_year_group` is removed from the current JSON and retained ONLY in the audit files. It is not
an API field or an eligibility restriction. Do not show “only years 3–4,” infer year 2+
from an internship title, or treat master year 1 as undergraduate year 1. Final-year jobs,
completed semesters by start, integrated masters and conditional degree lengths cannot
be reliably filtered by this array. Do not implement a competing interpretation in JS.

## How to display eligibility

- Null year/degree: “Not established — check the official requirements.” This also covers
  a confirmed rule that the current schema cannot represent accurately; consult the notes.
- Numeric list: show the supported academic-year dimension, then the extra conditions
  in description/the official source. It is not a guarantee that the student qualifies.
- `description` begins with the reviewed academic notes and official evidence URL.
  Its separately labeled historical research summary is not newly certified evidence.
- Year-2 encouragement for Arm Graphics applies to an integrated master programme;
  ordinary bachelor year 2 must not be declared eligible automatically.
- Four semesters COMPLETED BEFORE START is not “currently in year 2.”
- Stripe's one university year is a preference, not a hard eligibility cutoff.

All C2 candidates are `is_active=false`. Development previews can request
`is_active=false`; do not publish them as live opportunities. A future explicit publication
review must confirm availability, deadline timing, visa/geographical restrictions and
full requirements. A null deadline does not mean rolling applications. The date-only UTC
midnight value is not a verified exact closing time. `posted_at` stays null when unknown.
`skills` includes only evidence-recorded mandatory skills; an empty array is “not recorded,”
not “no skills required.” The current 50 rows have empty required/suggested skill arrays.



## Recorded local validation (15 October 2026)

These results were recorded before this documentation cleanup:

- Dry run: 50 accepted, 25 current verified, 25 flagged, 0 approved.
- Python suite: 113 passed; Ruff passed.
- Fresh migrations/RLS and repeat seed PGlite tests passed; 50 inactive rows after both runs.
- Minimum-40 check fails intentionally at 25/40; shared import is not ready.
- No shared C2 import, commit, push or PR was performed.

## Files to maintain

- `opportunities_seed.json`: canonical input; preserve unrelated local data.
- `eligibility_audit.json`: academic evidence/fingerprints required by validation.
- `source_verification.json`: current-source evidence/publication gates required by validation.
- [ELIGIBILITY_AUDIT.md](ELIGIBILITY_AUDIT.md): readable academic audit and representation limits for Maria.
- [SOURCE_VERIFICATION.md](SOURCE_VERIFICATION.md): readable current-source audit and blockers.
- `reconciliation.json`: historical per-record reconciliation decisions; later official evidence in the current ledgers takes precedence.
- `workbook_audit.csv`: supplied historical EUROPE MASTER review; not official eligibility or publication approval.

Workbook provenance covers 42 rows plus 8 supplemental rows. Maria's June 2029 graduate
shortlist is curation context, never proof of official academic-year eligibility. The original
workbook was not supplied. Research provenance and alternative supplied values remain in
the dataset and reconciliation ledger. Recommendation groups remain historical audit data.


## Authorized hosted import attempt (15 October 2026)

Dalia authorized importing the candidates and committing the local implementation.
The linked development project was fnldapsomswemayxhayk. The inactive SQL seed failed
because public.opportunities lacks degree_level (PostgreSQL error 42703). The transaction
rolled back: a follow-up query confirmed 0 total rows and 0 active rows. No schema changes
were applied. Apply the existing reviewed eligibility/type migrations through the normal
schema workflow before retrying the import. Unverified records remain unverified/inactive;
this authorization does not establish official eligibility or meet the minimum-40 criterion.
Local checks rerun before commit: 113 Python tests passed, Ruff passed, fresh migration/RLS
and repeat-seed PGlite tests passed. C2 remains In Progress.
