# database/seeds

Seed data for local development and tests.

# Opportunity Seed Dataset

`opportunities_seed.json` is the **ingestion input format**: the shape produced
by crawlers/normalizers and consumed by the ingestion pipeline. It is **not**
the database schema and **not** the API response shape — records are
transformed at ingestion time into the `opportunities` table / API contract.

## Input record format

| Field | Type | Required | Description / Permitted Values |
| :--- | :--- | :--- | :--- |
| `title` | `string` | Yes | Full title of the opportunity |
| `source` | `string` | Yes | Ingestion source namespace; `seed_dataset_v1` for every record here |
| `source_id` | `string` | Yes | Unique kebab-case slug derived from the title; stable within the source |
| `organization` | `string` | Yes | Sponsoring company, university, or institution name |
| `type` | `string` | Yes | Canonical category: `internship`, `job`, `scholarship`, `hackathon`, `grant`, `research`, `conference`, `summer_school`, `other` |
| `location` | `string` | Yes | Location format (`City, Country`) or working model: `Remote`, `Hybrid` |
| `degree_level` | `string` | Yes | Eligible academic degree: `bachelor`, `master`, or `both` |
| `study_year` | `array[int]` / `null` | No | Target eligible study years (e.g., `[2, 3]`), or `null` if open to all years |
| `deadline` | `string` (ISO date) | Yes | Strict application deadline in ISO format: `YYYY-MM-DD` |
| `source_url` | `string` (URL) | Yes | Direct official external link to the opportunity post/application |
| `description` | `string` | Yes | Clear summary of scope, expectations, and role responsibilities |
| `required_skills` | `array[string]` | Yes | Normalized key technologies, tools, or domain qualifications |

## Mapping to the Opportunity contract

At ingestion, each input record maps to the `opportunities` table / API shape as
follows:

- `type` → `opportunity_type`. The nine enum values are
  `internship | job | scholarship | hackathon | grant | research | conference | summer_school | other`.
- `source_url` → `url` (unique per opportunity).
- `required_skills` → skills, resolved by name and attached through the
  opportunities↔skills many-to-many association.
- `title`, `organization`, `location`, `degree_level`, `study_year`,
  `description` → same-named columns.
- `deadline` (ISO date) → `deadline` datetime (end of day, UTC).
- `id` (UUID), `is_active`, `posted_at` are derived at ingestion time, not
  present in the input.
- `source` + `source_id` form the idempotency key: they map to the unique
  `(source, source_id)` constraint on `opportunities`, so re-running ingestion
  updates the existing row instead of creating a duplicate.

## Data Validation Rules

1. **Date Format:** The `deadline` field must strictly follow the ISO 8601 calendar date format (`YYYY-MM-DD`).
2. **Canonical Enums:** The `type` attribute must only contain one of the 9 standardized enum values; synonyms or free-form abbreviations are prohibited.
3. **Normalized Skills:** All values within `required_skills` must use canonical naming conventions (e.g., `Python`, `C++`, `SQL`, `FastAPI`).
4. **Source Integrity:** Every record must provide an accessible, valid `source_url`.
   **Note:** the `source_url` values in this seed file are illustrative
   placeholders. They MUST be verified and replaced with live, checked URLs
   before any real ingestion run.
5. **Idempotency:** `(source, source_id)` must be unique per record; `source_id`
   slugs are derived deterministically from the title, which is unique across
   the dataset.
