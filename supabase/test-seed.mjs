import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { PGlite } from '@electric-sql/pglite';
import { readFile, readdir } from 'node:fs/promises';

// Supabase owns these roles/Auth objects. Stub their documented interface only;
// exercise every application migration against real, disposable PostgreSQL.
const db = new PGlite();
try {
  await db.exec(`
    CREATE ROLE anon NOLOGIN;
    CREATE ROLE authenticated NOLOGIN;
    CREATE ROLE service_role NOLOGIN BYPASSRLS;
    CREATE SCHEMA auth;
    CREATE TABLE auth.users (
      id uuid PRIMARY KEY, email text, raw_user_meta_data jsonb DEFAULT '{}'
    );
    CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
      $$ SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
    GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
    GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated, service_role;
  `);
  for (const file of (await readdir(new URL('./migrations/', import.meta.url))).filter(f => f.endsWith('.sql')).sort()) {
    await db.exec(await readFile(new URL(`./migrations/${file}`, import.meta.url), 'utf8'));
    console.log(`Applied ${file}`);
  }
  const records = JSON.parse(await readFile(new URL('../database/seeds/opportunities_seed.json', import.meta.url), 'utf8'));
  const expectedCount = records.length;
  const legacyCandidate = records[0];
  const sourceReview = JSON.parse(await readFile(new URL('../database/seeds/source_verification.json', import.meta.url), 'utf8'));
  const expectedSourceId = sourceReview.rows.find(row => row.source_url === legacyCandidate.url).official_source_id ?? legacyCandidate.source_id;
  const legacyUrl = new URL(legacyCandidate.url);
  const requisition = legacyUrl.pathname.match(/_([A-Za-z0-9-]+)$/)[1];
  const legacyKey = 'sha256:' + createHash('sha256').update(`${legacyUrl.hostname}/requisition/${requisition}`).digest('hex');
  const legacyUuid = 'c2000000-0000-4000-8000-000000000099';
  await db.query(`INSERT INTO public.opportunities (id,title,opportunity_type,url,source,source_id)
    VALUES ($1,'Legacy candidate','early_career',$2,'manual_seed_v1',$3)`, [legacyUuid,legacyCandidate.url,legacyKey]);
  await db.exec(`INSERT INTO auth.users (id,email) VALUES
    ('c2000000-0000-4000-8000-000000000002','legacy-c2@example.invalid')`);
  await db.query(`INSERT INTO public.applications (user_id,opportunity_id)
    VALUES ('c2000000-0000-4000-8000-000000000002',$1)`, [legacyUuid]);
  const seed = await readFile(new URL('./seed.sql', import.meta.url), 'utf8');
  await db.exec(seed);
  const snapshot = async () => (await db.query(
    "SELECT id, source_id, title, study_year, degree_level, is_active, updated_at FROM public.opportunities ORDER BY source_id"
  )).rows;
  const first = await snapshot();
  assert.equal(first.length, expectedCount);
  assert.equal(first.find(row => row.source_id === expectedSourceId).id, legacyUuid);
  assert.ok(first.every(row => row.is_active === false));
  assert.equal(first.filter(row => row.study_year !== null).length, 3);
  assert.equal(new Set(first.map(row => row.id)).size, expectedCount);
  assert.equal(new Set(first.map(row => row.source_id)).size, expectedCount);
  await db.exec(seed);
  assert.deepEqual(await snapshot(), first, 'Second import must not change IDs, values or timestamps');
  await db.exec(`INSERT INTO auth.users (id, email) VALUES
    ('c2000000-0000-4000-8000-000000000001', 'c2-test@example.invalid')`);
  await db.query(`INSERT INTO public.applications (user_id, opportunity_id)
    VALUES ('c2000000-0000-4000-8000-000000000001', $1)`, [first[0].id]);
  await db.query('UPDATE public.opportunities SET title = $1 WHERE id = $2', ['Locally edited', first[0].id]);
  await db.exec(seed);
  assert.deepEqual((await snapshot()).map(row => [row.id, row.title]), first.map(row => [row.id, row.title]));
  assert.equal((await db.query("SELECT opportunity_id FROM public.applications WHERE user_id = 'c2000000-0000-4000-8000-000000000001'")).rows[0].opportunity_id, first[0].id);
  assert.equal((await db.query('SELECT count(*)::int AS n FROM public.opportunities')).rows[0].n, expectedCount);
  await db.exec('SET ROLE anon');
  assert.equal((await db.query('SELECT count(*)::int AS n FROM public.opportunities WHERE is_active = true')).rows[0].n, 0);
  await db.exec('RESET ROLE');
  // Synthetic local publication fixture verifies browser-role read grants, not real approval.
  await db.query('UPDATE public.opportunities SET is_active = true WHERE id = $1', [first[0].id]);
  await db.exec('SET ROLE anon');
  assert.equal((await db.query('SELECT count(*)::int AS n FROM public.opportunities WHERE is_active = true')).rows[0].n, 1);
  await db.exec('RESET ROLE');
  await db.query('UPDATE public.opportunities SET is_active = false WHERE id = $1', [first[0].id]);
  console.log(`First import: ${expectedCount} rows; second import: ${expectedCount} rows; anon active query: 0 real approvals / 1 synthetic fixture`);
  await db.exec(await readFile(new URL('./tests/rls.sql', import.meta.url), 'utf8'));
  console.log(`PASS: ${expectedCount} inactive candidates, repeat import, unchanged timestamps, eligibility nulls, stable UUIDs, preserved applications and RLS`);
} finally {
  await db.close();
}
