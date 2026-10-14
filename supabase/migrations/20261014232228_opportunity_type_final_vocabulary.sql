-- Final opportunity_type vocabulary (11 values, decided 2026-10-14 by Maria, option A)
-- Aligns Supabase, the frozen API contract, the FastAPI model, and the seed dataset:
--   internship, job, research, scholarship, fellowship, hackathon,
--   competition, early_career, open_source, grant, other

ALTER TYPE public.opportunity_type ADD VALUE IF NOT EXISTS 'research';
ALTER TYPE public.opportunity_type ADD VALUE IF NOT EXISTS 'competition';
ALTER TYPE public.opportunity_type ADD VALUE IF NOT EXISTS 'open_source';

DO $$
BEGIN
    -- early_program is renamed, not kept alongside early_career: one concept, one name.
    IF EXISTS (
        SELECT 1
        FROM pg_enum e
        JOIN pg_type t ON t.oid = e.enumtypid
        WHERE t.typname = 'opportunity_type' AND e.enumlabel = 'early_program'
    ) THEN
        ALTER TYPE public.opportunity_type RENAME VALUE 'early_program' TO 'early_career';
    END IF;
END $$;
