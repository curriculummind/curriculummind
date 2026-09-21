-- Decision 024: a teacher links students via a class code instead of the
-- deferred parent-invite-by-email flow. A teacher's profile carries a
-- unique class_code; a student redeems one at signup, which creates
-- their guardian_links row atomically with their own profile (see
-- app/identity/profiles.py's create_profile).
--
-- The check constraint keeps "only teachers have a code" a database
-- guarantee, not just an application convention -- the same posture
-- Decision 009/010 already take toward guardian-boundary invariants.
--
-- No new RLS policy is needed: profiles' existing "readable/updatable
-- by their owner" policies already cover this new column per-row. The
-- class-code lookup itself (matching a student's submitted code to a
-- teacher) never runs through a client-side Supabase call -- it happens
-- inside the backend's own connection, per Decision 010 -- so RLS was
-- never going to be the enforcement point for that lookup anyway.

alter table profiles add column class_code text;

alter table profiles
  add constraint profiles_class_code_unique unique (class_code);

alter table profiles
  add constraint profiles_class_code_matches_role
  check ((role = 'teacher') = (class_code is not null));
