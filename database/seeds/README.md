# Opportunity Seed Dataset (C1)

This directory contains `opportunities_seed.json`, the candidate opportunity dataset for the **Opportunity Tracker** project. The file is a UTF-8 JSON array intended for review, filtering, development, and testing. The project's planned database is **Supabase (managed PostgreSQL)**.


## Current dataset snapshot

- **50 records**, all in one JSON array, from the research spreadsheet prepared on **2026-10-12**.
- **28** recommended for study-year group `1-2`; **22** for `3-4`.
- **29 fields** on every record. Values may be `null`, `[]`, or qualified free text when the source does not establish a specific requirement.
- Current `type` distribution (after the 2026-10-14 vocabulary decision):

| Category (`type`) | Records |
| :--- | ---: |
| `internship` | 13 |
| `early_career` | 13 |
| `hackathon` | 9 |
| `research` | 8 |
| `competition` | 3 |
| `open_source` | 2 |
| `job` | 2 |
| **Total** | **50** |

The final `opportunity_type` vocabulary (**11 values**, decided by Maria on
2026-10-14, option A) is: `internship`, `job`, `research`, `scholarship`,
`fellowship`, `hackathon`, `competition`, `early_career`, `open_source`,
`grant`, `other`. It is the single source of truth shared by the Supabase enum
(`supabase/migrations`), the frozen API contract (`docs/api.md`), and the
FastAPI model (`OpportunityType`). Seed-specific changes applied here:
`campus_ambassador` → `early_career` (3 records). Categories with no current
records (`scholarship`, `fellowship`, `grant`, `other`) remain valid enum
values for future imports.

## JSON schema reference

“Present” means that the key exists on each of the current 50 objects; it does **not** imply a non-null, externally verified value. Types below describe the JSON seed file, not PostgreSQL column types.

### Core opportunity fields

| Field | JSON type | Meaning / rule |
| :--- | :--- | :--- |
| `title` | `string` | Name of the specific opportunity. Titles need not be globally unique. |
| `organization` | `string` | Company, university, nonprofit, or event organizer. |
| `type` | `string` | One of the eight category values listed above. |
| `location` | `string` | Descriptive location (such as `London, UK`); **do not** infer work arrangement from this field. |
| `degree_level` | `string \| null` | Current values: `bachelor`, `both`, or `null`; reserve `master` for a future confirmed record if approved. `null` means unknown, not unrestricted. |
| `study_year` | `array[integer] \| null` | Study years explicitly supported by eligibility evidence, e.g. `[1, 2]`. `null` means not established; **not** automatically all years. |
| `deadline` | `string \| null` | Confirmed application/registration cutoff as `YYYY-MM-DD`; `null` if unknown or not applicable. Recheck the official source. |
| `source_url` | `string` | Opportunity-related reference URL. It must be manually checked for accuracy, authority, accessibility, and current status. |
| `description` | `string` | Short summary derived from research notes; may still require additional review against the official listing. |
| `required_skills` | `array[string]` | Skills confirmed as mandatory. `[]` means none were recorded/confirmed, **not** that none are required. |
| `suggested_skills` | `array[string]` | Explicitly recommended or preferred skills. `[]` means none were recorded/confirmed. |
| `eligible_countries` | `array[string] \| null` | Confirmed applicant-eligibility countries. `null` means eligibility has not been established; **do not** infer Romania or worldwide access from event location or a remote label. If populated, agree on a country naming standard with Maria. |
| `years_of_experience` | `integer \| null` | Confirmed minimum professional experience. Use `0` **only** if a source explicitly permits no experience; use `null` when unspecified. |
| `released_date` | `string \| null` | Confirmed publication/release date as `YYYY-MM-DD`; `null` if unavailable. Do not confuse it with `date_checked`. |

### Student matching, participation, and scheduling

| Field | JSON type | Meaning / rule |
| :--- | :--- | :--- |
| `study_year_group` | `string` | Research/recommendation grouping: `1-2` or `3-4`. **Not a proof of eligibility.** |
| `eligibility_notes` | `string` | Free-text source-based criteria, including graduation year, penultimate/final year, age, nationality, visa/work authorization, or exceptions. Check for updates. |
| `application_status` | `string` | Human-readable status/notes captured at research time; **not a live status** or canonical enum. |
| `participation_mode` | `string` | Descriptive wording (e.g., `On-site (London)`, `Remote (online)`, staged hybrid, or `Not specified`). |
| `work_mode` | `string \| null` | Normalized value: `on_site`, `remote`, `hybrid`, or `null` where unconfirmed. A staged event can use `hybrid`; see `duration_format_notes`. |
| `schedule_commitment` | `string` | Free-text working time/commitment, such as `Full-time`, `Part-time`, `Not specified`, or `N/A — hackathon`. Do not treat one-off events as employment schedules. |
| `duration_format_notes` | `string` | Specific duration, event dates, participation arrangement, caveats, or clarification of hybrid/staged programs. |
| `format_source_url` | `string` | URL used to support participation mode, commitment, or duration; content must still be checked. |

### Review and provenance metadata

| Field | JSON type | Meaning / rule |
| :--- | :--- | :--- |
| `verification_source_url` | `string` | Reference used to check the opportunity's details. A stored URL alone does not establish completed verification. |
| `verification_level` | `string` | Human-readable research/provenance note; not a machine-readable verification guarantee. |
| `maria_audit_verdict` | `string` | Verdict text copied from or associated with Maria's opportunity audit / subsequent recheck; preserve the original context. |
| `c1_readiness` | `string` | Human-readable review category (`C1 candidate`, `Individual verification required`, etc.), **not** proof of production readiness. |
| `verification_notes` | `string` | Evidence, caveats, and follow-up instructions retained from research. |
| `source_origin` | `string` | How the record entered the shortlist, such as Maria's master sheet, a company posting, or Devpost. |
| `date_checked` | `string` | Research check date in `YYYY-MM-DD` format. This is **not** the posting date and does not guarantee the information remains current. |

## Missing data and current limitations

The JSON is syntactically valid, but it is **not yet a fully enriched or fully reverified seed**:

- All 50 `eligible_countries`, `years_of_experience`, and `released_date` values are currently `null`.
- All 50 `required_skills` and `suggested_skills` arrays are currently empty. They must be filled from official requirements, rather than guessed.
- `study_year` is `null` in 43 records; `study_year_group` is therefore a *recommendation label*, not a reliable eligibility filter for those records.
- `deadline` is `null` in 31 records. Registration may be closed, not yet announced, or unspecified; `null` does **not** mean rolling applications.
- Nine records have `c1_readiness: "Individual verification required"`. Other readiness labels also do not waive source review.
- Several statuses and deadlines are time-sensitive; `date_checked` is `2026-10-12` for this snapshot. Revisit them before publishing or importing.
- The same opportunity title may occur at more than one location. Compare official posting IDs, URLs, organization, role, and location before deduplication; **do not deduplicate by title alone**.

## Validation and quality rules

1. **JSON structure:** The file must parse into a top-level array of opportunity objects. Keep the keys and types consistent across records.
2. **Categories:** `type` must be one of the 11 final vocabulary values listed above (decided 2026-10-14 by Maria). Do not introduce synonyms or new values without a contract change per ADR 0002.
3. **Dates:** Non-null `deadline`, `released_date`, and `date_checked` values must be genuine calendar dates in `YYYY-MM-DD` format. A date's format alone does not prove accuracy.
4. **Source integrity:** Verify that `source_url` points to a relevant official company/organizer listing, not an unrelated homepage. `format_source_url` should substantiate the claimed remote/on-site/hybrid arrangements and duration. If the page is unavailable, flag the record.
5. **Geographic eligibility:** Check Romania-specific eligibility and any residency, nationality, visa, work authorization, age, or on-site travel conditions. Record only what the official source supports.
6. **Academic eligibility:** Distinguish confirmed `study_year` restrictions from `study_year_group` recommendations. Prefer the actual wording of final-year, penultimate-year, or expected-graduation requirements in `eligibility_notes`.
7. **Skills and experience:** Record explicitly required versus preferred skills separately. Do not infer `0` experience or add skills just because they are common for the role.
8. **Participation arrangement:** Normalize `work_mode` only when supported; keep nuances in `participation_mode` and `duration_format_notes`. `schedule_commitment` is an employment schedule only for employment-like opportunities.
9. **Unknown versus not applicable:** Use `null` for unknown scalar facts where the schema allows it, `[]` for skills not recorded, and explanatory text such as `N/A — hackathon` for non-applicable schedules. Do not replace unknowns with fictional defaults.
10. **Duplicates:** Reject duplicate opportunity-specific `source_url` values unless the team has documented a legitimate reason. Different locations/postings can share a title.
11. **Review gates:** Compare each source against the live posting, fix stale statuses, and resolve records needing individual verification before marking them import-ready.


## Supabase and task boundaries

- **C1 (this directory):** Research, clean, document, and review the seed JSON; preserve provenance and unresolved issues.
- **C2 (separate task):** Map approved fields into Maria's reviewed Supabase/PostgreSQL schema, implement the import, and handle deduplication and errors.
- **Schema coordination:** The category enum is now decided (11 values, 2026-10-14). `degree_level` and `study_year` have target columns since migration `20261014233344_opportunity_eligibility_fields` (`opportunities.degree_level` of enum `opportunity_degree_level`, `opportunities.study_year` jsonb — both nullable, `null` = not established). Remaining mappings to agree in C2: review-metadata handling and the `id`/`source`/`source_id` derivation.
- **Security:** Keep Supabase connection secrets and service-role keys in local environment variables; do not commit `.env` files, tokens, or credentials.

## Pre-import checklist

- [ ] All 50 individual listings are reviewed against official sources; broken links and expired calls are flagged.
- [ ] Romanian applicant eligibility, academic/graduation-year restrictions, and work authorization are assessed where relevant.
- [ ] The team confirms category enums, field names/types, nullability, and mappings to the PostgreSQL schema.
- [ ] Unknown or stale application status is handled explicitly; availability is not assumed.
- [ ] Required/preferred skills and source-backed experience requirements are populated where published.
- [ ] No unintended duplicate postings exist; official source identifiers are checked.
