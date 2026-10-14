
-- C1: Row Level Security policies
-- User-owned data is private.
-- Shared catalogs are read-only for clients.

-- 1. ENABLE RLS

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.opportunity_skills ENABLE ROW LEVEL SECURITY;


-- 2. EXPLICIT CLIENT PERMISSIONS
-- Remove existing permissions for browser-facing roles.

REVOKE ALL ON TABLE
    public.users,
    public.profiles,
    public.skills,
    public.opportunities,
    public.applications,
    public.user_skills,
    public.opportunity_skills
FROM anon, authenticated;

-- Users can only read their own user record.
GRANT SELECT ON public.users TO authenticated;

-- Users can create and edit their own profiles.
GRANT SELECT, INSERT, UPDATE
ON public.profiles TO authenticated;

-- Users can manage their own tracked applications.
GRANT SELECT, INSERT, UPDATE, DELETE
ON public.applications TO authenticated;

-- Users can manage their own skill associations.
GRANT SELECT, INSERT, DELETE
ON public.user_skills TO authenticated;

-- Shared catalogs are readable, but not writable.
GRANT SELECT ON
    public.skills,
    public.opportunities,
    public.opportunity_skills
TO anon, authenticated;


-- 3. USERS POLICIES

CREATE POLICY "Users can view their own record"
ON public.users
FOR SELECT
TO authenticated
USING (
    (SELECT auth.uid()) = id
);


-- 4. PROFILES POLICIES

CREATE POLICY "Users can view their own profile"
ON public.profiles
FOR SELECT
TO authenticated
USING (
    (SELECT auth.uid()) = user_id
);

CREATE POLICY "Users can insert their own profile"
ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK (
    (SELECT auth.uid()) = user_id
);

CREATE POLICY "Users can update their own profile"
ON public.profiles
FOR UPDATE
TO authenticated
USING (
    (SELECT auth.uid()) = user_id
)
WITH CHECK (
    (SELECT auth.uid()) = user_id
);


-- 5. APPLICATIONS POLICIES

CREATE POLICY "Users can view their own applications"
ON public.applications
FOR SELECT
TO authenticated
USING (
    (SELECT auth.uid()) = user_id
);

CREATE POLICY "Users can create their own applications"
ON public.applications
FOR INSERT
TO authenticated
WITH CHECK (
    (SELECT auth.uid()) = user_id
);

CREATE POLICY "Users can update their own applications"
ON public.applications
FOR UPDATE
TO authenticated
USING (
    (SELECT auth.uid()) = user_id
)
WITH CHECK (
    (SELECT auth.uid()) = user_id
);

CREATE POLICY "Users can delete their own applications"
ON public.applications
FOR DELETE
TO authenticated
USING (
    (SELECT auth.uid()) = user_id
);


-- 6. USER SKILLS POLICIES

CREATE POLICY "Users can view their own skills"
ON public.user_skills
FOR SELECT
TO authenticated
USING (
    (SELECT auth.uid()) = user_id
);

CREATE POLICY "Users can add their own skills"
ON public.user_skills
FOR INSERT
TO authenticated
WITH CHECK (
    (SELECT auth.uid()) = user_id
);

CREATE POLICY "Users can remove their own skills"
ON public.user_skills
FOR DELETE
TO authenticated
USING (
    (SELECT auth.uid()) = user_id
);


-- 7. SHARED SKILLS CATALOG

CREATE POLICY "Skills catalog is readable"
ON public.skills
FOR SELECT
TO anon, authenticated
USING (true);


-- 8. OPPORTUNITIES CATALOG

CREATE POLICY "Opportunities are readable"
ON public.opportunities
FOR SELECT
TO anon, authenticated
USING (true);


-- 9. OPPORTUNITY SKILLS CATALOG

CREATE POLICY "Opportunity skills are readable"
ON public.opportunity_skills
FOR SELECT
TO anon, authenticated
USING (true);
