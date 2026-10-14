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
  await db.exec(await readFile(new URL('./tests/rls.sql', import.meta.url), 'utf8'));
  console.log('PASS: fresh PostgreSQL migration replay and RLS/Auth behavior');
} finally {
  await db.close();
}
