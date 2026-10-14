-- Keep public identity rows synchronized with Supabase Auth, including existing users.
-- No browser role may execute the privileged trigger function directly.
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated;
CREATE FUNCTION private.sync_auth_user()
RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.users (id, email, full_name)
    VALUES (NEW.id, COALESCE(NEW.email, ''),
            left(COALESCE(NEW.raw_user_meta_data ->> 'full_name', ''), 255))
    ON CONFLICT (id) DO UPDATE
      SET email = EXCLUDED.email, full_name = EXCLUDED.full_name;
    INSERT INTO public.profiles (user_id) VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION private.sync_auth_user() FROM PUBLIC, anon, authenticated;
CREATE TRIGGER sync_auth_user
AFTER INSERT OR UPDATE OF email, raw_user_meta_data ON auth.users
FOR EACH ROW EXECUTE FUNCTION private.sync_auth_user();
INSERT INTO public.users (id, email, full_name)
SELECT id, COALESCE(email, ''), left(COALESCE(raw_user_meta_data ->> 'full_name', ''), 255)
FROM auth.users
ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, full_name = EXCLUDED.full_name;
INSERT INTO public.profiles (user_id)
SELECT id FROM public.users ON CONFLICT (user_id) DO NOTHING;
-- Explicit server-side ingestion permissions; service_role bypasses RLS.
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON TABLE public.users, public.profiles, public.skills, public.opportunities,
    public.applications, public.user_skills, public.opportunity_skills TO service_role;
CREATE INDEX ix_user_skills_skill_id ON public.user_skills (skill_id);
CREATE INDEX ix_opportunity_skills_skill_id ON public.opportunity_skills (skill_id);
