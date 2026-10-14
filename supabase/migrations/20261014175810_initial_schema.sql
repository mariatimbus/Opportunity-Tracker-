
-- C1: Supabase foundation
-- Initial database schema for Opportunity Tracker

-- 1. ENUM TYPES

CREATE TYPE public.opportunity_type AS ENUM (
    'internship',
    'job',
    'scholarship',
    'hackathon',
    'fellowship',
    'early_program',
    'grant',
    'other'
);

CREATE TYPE public.application_status AS ENUM (
    'saved',
    'applied',
    'interview',
    'offer',
    'rejected'
);

CREATE TYPE public.degree_level AS ENUM (
    'bachelor',
    'master'
);


-- 2. USERS
-- User identity is managed by Supabase Auth.

CREATE TABLE public.users (
    id UUID PRIMARY KEY
        REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_users_email
    ON public.users(email);


-- 3. SKILLS

CREATE TABLE public.skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_skills_name
    ON public.skills(name);


-- 4. OPPORTUNITIES

CREATE TABLE public.opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    organization VARCHAR(255),
    opportunity_type public.opportunity_type NOT NULL,
    location VARCHAR(255),
    url VARCHAR(512) NOT NULL UNIQUE,
    source VARCHAR(100) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    deadline TIMESTAMPTZ,
    posted_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_opportunity_source_source_id
        UNIQUE (source, source_id)
);


-- 5. PROFILES

CREATE TABLE public.profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE
        REFERENCES public.users(id) ON DELETE CASCADE,
    headline VARCHAR(255),
    bio TEXT,
    location VARCHAR(255),
    resume_url VARCHAR(512),
    degree_level public.degree_level,
    field_of_study VARCHAR(255),
    university VARCHAR(255),
    graduation_year INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 6. APPLICATIONS

CREATE TABLE public.applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES public.users(id) ON DELETE CASCADE,
    opportunity_id UUID NOT NULL
        REFERENCES public.opportunities(id) ON DELETE CASCADE,
    status public.application_status NOT NULL DEFAULT 'saved',
    notes TEXT,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_application_user_opportunity
        UNIQUE (user_id, opportunity_id)
);

CREATE INDEX ix_applications_user_id
    ON public.applications(user_id);

CREATE INDEX ix_applications_opportunity_id
    ON public.applications(opportunity_id);


-- 7. USER SKILLS

CREATE TABLE public.user_skills (
    user_id UUID NOT NULL
        REFERENCES public.users(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL
        REFERENCES public.skills(id) ON DELETE CASCADE,

    PRIMARY KEY (user_id, skill_id)
);


-- 8. OPPORTUNITY SKILLS

CREATE TABLE public.opportunity_skills (
    opportunity_id UUID NOT NULL
        REFERENCES public.opportunities(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL
        REFERENCES public.skills(id) ON DELETE CASCADE,

    PRIMARY KEY (opportunity_id, skill_id)
);


-- 9. AUTOMATIC UPDATED_AT TIMESTAMPS

CREATE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER skills_updated_at
BEFORE UPDATE ON public.skills
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER opportunities_updated_at
BEFORE UPDATE ON public.opportunities
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER applications_updated_at
BEFORE UPDATE ON public.applications
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- 10. ENABLE ROW LEVEL SECURITY
-- Access policies will be added in the next migration.

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.opportunity_skills ENABLE ROW LEVEL SECURITY;
