-- Run only against a development/disposable Supabase project. All fixtures roll back.
BEGIN;
INSERT INTO auth.users (id, email, raw_user_meta_data) VALUES
 ('c1000000-0000-4000-8000-000000000001', 'c1-a@example.invalid', '{"full_name":"Fixture A"}'),
 ('c1000000-0000-4000-8000-000000000002', 'c1-b@example.invalid', '{"full_name":"Fixture B"}');
INSERT INTO public.skills (id, name) VALUES ('c1000000-0000-4000-8000-000000000003', 'C1 fixture skill');
INSERT INTO public.opportunities (id, title, opportunity_type, url, source, source_id) VALUES
 ('c1000000-0000-4000-8000-000000000004', 'C1 fixture', 'internship', 'https://example.invalid/c1-rls', 'c1-test', 'rls');
INSERT INTO public.opportunity_skills VALUES
 ('c1000000-0000-4000-8000-000000000004', 'c1000000-0000-4000-8000-000000000003');
DO $$ BEGIN
 IF (SELECT count(*) FROM public.profiles WHERE user_id IN
 ('c1000000-0000-4000-8000-000000000001', 'c1000000-0000-4000-8000-000000000002')) <> 2
 THEN RAISE EXCEPTION 'Auth profile bootstrap failed'; END IF;
 IF (SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity
 AND tablename IN ('users','profiles','skills','opportunities','applications','user_skills','opportunity_skills')) <> 7
 THEN RAISE EXCEPTION 'RLS missing'; END IF;
END $$;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', 'c1000000-0000-4000-8000-000000000001', true);
DO $$ BEGIN
 IF (SELECT count(*) FROM public.users) <> 1 OR (SELECT count(*) FROM public.profiles) <> 1
 THEN RAISE EXCEPTION 'User A isolation failed'; END IF;
 UPDATE public.profiles SET headline = 'Owner edit' WHERE user_id = auth.uid();
 INSERT INTO public.applications (user_id, opportunity_id) VALUES
 (auth.uid(), 'c1000000-0000-4000-8000-000000000004');
 INSERT INTO public.user_skills VALUES (auth.uid(), 'c1000000-0000-4000-8000-000000000003');
 BEGIN
  INSERT INTO public.applications (user_id, opportunity_id) VALUES
  ('c1000000-0000-4000-8000-000000000002', 'c1000000-0000-4000-8000-000000000004');
  RAISE EXCEPTION 'Cross-user insert allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN
  UPDATE public.users SET is_active = false;
  RAISE EXCEPTION 'Client identity update allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN
  INSERT INTO public.skills (name) VALUES ('Forbidden catalog write');
  RAISE EXCEPTION 'Catalog write allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
SELECT set_config('request.jwt.claim.sub', 'c1000000-0000-4000-8000-000000000002', true);
DO $$ BEGIN
 IF (SELECT count(*) FROM public.users) <> 1 OR (SELECT count(*) FROM public.profiles) <> 1
 OR (SELECT count(*) FROM public.applications) <> 0 OR (SELECT count(*) FROM public.user_skills) <> 0
 THEN RAISE EXCEPTION 'User B isolation failed'; END IF;
 UPDATE public.profiles SET headline = 'Stolen' WHERE user_id = 'c1000000-0000-4000-8000-000000000001';
 IF FOUND THEN RAISE EXCEPTION 'Cross-user profile update allowed'; END IF;
 DELETE FROM public.applications;
 IF FOUND THEN RAISE EXCEPTION 'Cross-user delete allowed'; END IF;
 INSERT INTO public.applications (user_id, opportunity_id) VALUES
 (auth.uid(), 'c1000000-0000-4000-8000-000000000004');
 UPDATE public.applications SET status = 'applied' WHERE user_id = auth.uid();
 DELETE FROM public.applications WHERE user_id = auth.uid();
END $$;
SET LOCAL ROLE anon;
DO $$ BEGIN
 PERFORM * FROM public.skills;
 PERFORM * FROM public.opportunities;
 PERFORM * FROM public.opportunity_skills;
 BEGIN
  PERFORM * FROM public.profiles;
  RAISE EXCEPTION 'Anonymous private access allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE;
UPDATE auth.users SET email = 'c1-updated@example.invalid'
WHERE id = 'c1000000-0000-4000-8000-000000000001';
DO $$ BEGIN
 IF (SELECT email FROM public.users WHERE id = 'c1000000-0000-4000-8000-000000000001') <> 'c1-updated@example.invalid'
 THEN RAISE EXCEPTION 'Auth email synchronization failed'; END IF;
END $$;
DELETE FROM auth.users WHERE id = 'c1000000-0000-4000-8000-000000000001';
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM public.profiles WHERE user_id = 'c1000000-0000-4000-8000-000000000001')
 OR EXISTS (SELECT 1 FROM public.applications WHERE user_id = 'c1000000-0000-4000-8000-000000000001')
 OR EXISTS (SELECT 1 FROM public.user_skills WHERE user_id = 'c1000000-0000-4000-8000-000000000001')
 THEN RAISE EXCEPTION 'Auth deletion cascade failed'; END IF;
END $$;
ROLLBACK;
SELECT 'PASS: Auth synchronization, two-user isolation, anonymous/catalog permissions and deletion cascades' AS result;
