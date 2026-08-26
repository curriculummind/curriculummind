-- Content-safety guardrail (Decision 022): records every turn the safety
-- classifier flags, whether or not it was actually blocked, so nothing
-- is thrown away before Pillar B's guardian dashboard exists to read it.
--
-- Per Decision 009 (see initial schema comment), guardians never get RLS
-- access to raw conversation data -- only a student can read their own
-- flagged rows here. Guardian visibility is deferred to a
-- backend-mediated derived summary, not direct table access, when the
-- dashboard is built.
create table flagged_interactions (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations (id) on delete cascade,
  student_id uuid not null references profiles (id) on delete cascade,
  category text not null check (category in ('prompt_injection', 'unsafe_content', 'crisis', 'sensitive_topic', 'pii')),
  question text not null,
  blocked boolean not null,
  created_at timestamptz not null default now()
);

alter table flagged_interactions enable row level security;

create policy "flagged interactions are readable by the student"
  on flagged_interactions for select
  using (auth.uid() = student_id);
