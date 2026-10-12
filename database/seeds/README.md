# database/seeds

Seed data for local development and tests. Placeholder for now.

# Opportunity Seed Dataset

This directory contains the initial seed dataset (`opportunities_seed.json`) used to bootstrap and populate the database (PostgreSQL / Supabase) across development and testing environments.

## Schema Specification

Each opportunity record adheres to the following structure:

| Field | Type | Required | Description / Permitted Values |
| :--- | :--- | :--- | :--- |
| `title` | `string` | Yes | Full title of the opportunity |
| `organization` | `string` | Yes | Sponsoring company, university, or institution name |
| `type` | `string` | Yes | Canonical category: `internship`, `research`, `scholarship`, `hackathon`, `conference`, `summer_school` |
| `location` | `string` | Yes | Location format (`City, Country`) or working model: `Remote`, `Hybrid` |
| `degree_level` | `string` | Yes | Eligible academic degree: `bachelor`, `master`, or `both` |
| `study_year` | `array[int]` / `null` | No | Target eligible study years (e.g., `[2, 3]`), or `null` if open to all years |
| `deadline` | `string` (ISO date) | Yes | Strict application deadline in ISO format: `YYYY-MM-DD` |
| `source_url` | `string` (URL) | Yes | Direct official external link to the opportunity post/application |
| `description` | `string` | Yes | Clear summary of scope, expectations, and role responsibilities |
| `required_skills` | `array[string]` | Yes | Normalized key technologies, tools, or domain qualifications |

## Data Validation Rules

1. **Date Format:** The `deadline` field must strictly follow the ISO 8601 calendar date format (`YYYY-MM-DD`).
2. **Canonical Enums:** The `type` attribute must only contain one of the 6 standardized enum values; synonyms or free-form abbreviations are prohibited.
3. **Normalized Skills:** All values within `required_skills` must use canonical naming conventions (e.g., `Python`, `C++`, `SQL`, `FastAPI`).
4. **Source Integrity:** Every record must provide an accessible, valid `source_url`.