-- Decision 034: a parent links directly to their own child instead of
-- going through a teacher's class code -- the mirror image of Decision
-- 024's mechanism, not a new one. A student's profile now carries a
-- unique student_link_code (generated the same way a teacher's
-- class_code already is); a guardian redeems one at signup, the same
-- shape as a student redeeming a class_code today.
--
-- subscription_status is the stubbed premium gate (a daily question
-- cap in app/tutoring/router.py checks it) -- no real billing wired up
-- yet, flipped directly via backend/scripts/set_subscription_status.py
-- during this phase.
--
-- waitlist_signups is unrelated to the above and has no RLS policies:
-- all writes go through the backend's own connection (POST /waitlist),
-- never a client-side Supabase call, so there is nothing for a public
-- policy to grant -- same posture class_code's lookup already takes.

alter table profiles add column student_link_code text;

-- Backfill any pre-existing student rows (pre-launch dev/test data only
-- -- real signups going forward always get a proper code from
-- _generate_short_code) so the check constraint below doesn't reject
-- them. Relies on gen_random_uuid()'s own randomness for uniqueness
-- among the small number of existing rows, not the production alphabet.
update profiles set student_link_code = upper(replace(gen_random_uuid()::text, '-', ''))
  where role = 'student' and student_link_code is null;

alter table profiles
  add constraint profiles_student_link_code_unique unique (student_link_code);

alter table profiles
  add constraint profiles_student_link_code_matches_role
  check ((role = 'student') = (student_link_code is not null));

alter table profiles add column subscription_status text not null default 'free'
  check (subscription_status in ('free', 'premium'));

create table waitlist_signups (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  interest text not null check (interest in ('parent', 'teacher')),
  created_at timestamptz not null default now(),
  unique (email)
);

alter table waitlist_signups enable row level security;
