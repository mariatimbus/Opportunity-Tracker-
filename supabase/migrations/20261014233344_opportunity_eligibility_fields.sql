-- Opportunity eligibility fields (C2, decided 2026-10-14 by Maria)
-- Backs the seed dataset's degree_level / study_year fields so the importer
-- (C2) has target columns. Both nullable: null means "not established" per
-- the seed semantics, NOT "open to everyone".

-- Separate from public.degree_level (profiles): that enum describes the
-- student's own degree and has no 'both' value.
CREATE TYPE public.opportunity_degree_level AS ENUM (
    'bachelor',
    'master',
    'both'
);

ALTER TABLE public.opportunities
    ADD COLUMN degree_level public.opportunity_degree_level,
    ADD COLUMN study_year jsonb;
