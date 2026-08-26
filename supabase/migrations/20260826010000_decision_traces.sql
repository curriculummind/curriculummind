-- Decision-trace persistence (Decision 023): the tutoring pipeline's own
-- per-turn decisions (safety category, retrieval band, chosen strategy,
-- evidence used, assignment/correctness flags, escalation state
-- transition) are computed every request already and were being thrown
-- away the moment the response finished streaming.
--
-- Per architecture §23 / app/observability/__init__.py's original
-- docstring: admin-only, never exposed to students or guardians. RLS is
-- enabled with no select or insert policy for any client role -- only
-- the backend's own privileged connection can read or write this table.
create table decision_traces (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations (id) on delete cascade,
  student_id uuid not null references profiles (id) on delete cascade,
  question text not null,
  safety_category text not null default 'none',
  band text,
  strategy text,
  is_assignment boolean,
  evidence_chunk_ids uuid[] not null default '{}',
  correctness text,
  tutoring_phase_before text not null,
  tutoring_phase_after text not null,
  struggle_count_before int not null,
  struggle_count_after int not null,
  confirm_count_before int not null,
  confirm_count_after int not null,
  created_at timestamptz not null default now()
);

alter table decision_traces enable row level security;
