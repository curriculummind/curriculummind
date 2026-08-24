-- Initial schema: identity, curriculum modeling, content chunks, and
-- conversation memory. Covers the M0 vertical slice (auth -> grounded
-- response -> persisted conversation). Decision trace, hint events,
-- learning context, evaluation results, and alerts are added in a later
-- migration once the evaluation/observability modules are built.
--
-- See architecture proposal §7 (Domain Model) and §13 (Curriculum
-- Architecture), and Decisions 008-010.

create extension if not exists vector;
create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------
-- Identity (§19, Decision 009: guardians never get RLS access to raw
-- conversation data -- only to a derived summary table added later)
-- ---------------------------------------------------------------------

create table profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  role text not null check (role in ('student', 'guardian', 'teacher')),
  display_name text not null,
  grade_level int,
  created_at timestamptz not null default now()
);

create table guardian_links (
  id uuid primary key default gen_random_uuid(),
  guardian_id uuid not null references profiles (id) on delete cascade,
  student_id uuid not null references profiles (id) on delete cascade,
  status text not null default 'active' check (status in ('active', 'revoked')),
  created_at timestamptz not null default now(),
  unique (guardian_id, student_id)
);

alter table profiles enable row level security;
alter table guardian_links enable row level security;

create policy "profiles are readable by their owner"
  on profiles for select
  using (auth.uid() = id);

create policy "profiles are updatable by their owner"
  on profiles for update
  using (auth.uid() = id);

create policy "guardian links are readable by either party"
  on guardian_links for select
  using (auth.uid() = guardian_id or auth.uid() = student_id);

-- ---------------------------------------------------------------------
-- Curriculum (§13: Concept is curriculum-agnostic; CurriculumFramework
-- and Standard attach to it as a mapping layer, not the other way round)
-- ---------------------------------------------------------------------

create table subjects (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null
);

create table concepts (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null references subjects (id) on delete cascade,
  slug text not null,
  name text not null,
  grade_band text not null,
  unique (subject_id, slug)
);

create table curriculum_frameworks (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  country text
);

create table standards (
  id uuid primary key default gen_random_uuid(),
  framework_id uuid not null references curriculum_frameworks (id) on delete cascade,
  code text not null,
  description text,
  unique (framework_id, code)
);

create table concept_standards (
  concept_id uuid not null references concepts (id) on delete cascade,
  standard_id uuid not null references standards (id) on delete cascade,
  primary key (concept_id, standard_id)
);

-- ---------------------------------------------------------------------
-- Curriculum content (§15: retrievable teaching material, distinct from
-- the standards documents in the tables above)
-- ---------------------------------------------------------------------

create table curriculum_resources (
  id uuid primary key default gen_random_uuid(),
  concept_id uuid not null references concepts (id) on delete cascade,
  source text not null,
  license text not null,
  source_url text,
  title text not null,
  grade_band text not null,
  ingested_at timestamptz not null default now()
);

create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  resource_id uuid not null references curriculum_resources (id) on delete cascade,
  chunk_index int not null,
  content text not null,
  embedding vector (1536),
  created_at timestamptz not null default now()
);

create index document_chunks_embedding_idx
  on document_chunks using hnsw (embedding vector_cosine_ops);

alter table subjects enable row level security;
alter table concepts enable row level security;
alter table curriculum_frameworks enable row level security;
alter table standards enable row level security;
alter table curriculum_resources enable row level security;
alter table document_chunks enable row level security;

create policy "curriculum content is readable by any authenticated user"
  on subjects for select to authenticated using (true);
create policy "curriculum content is readable by any authenticated user"
  on concepts for select to authenticated using (true);
create policy "curriculum content is readable by any authenticated user"
  on curriculum_frameworks for select to authenticated using (true);
create policy "curriculum content is readable by any authenticated user"
  on standards for select to authenticated using (true);
create policy "curriculum content is readable by any authenticated user"
  on curriculum_resources for select to authenticated using (true);
create policy "curriculum content is readable by any authenticated user"
  on document_chunks for select to authenticated using (true);

-- ---------------------------------------------------------------------
-- Conversation memory (§12: short-term, per-thread -- distinct from the
-- longer-term student learning context added in a later migration)
-- ---------------------------------------------------------------------

create table conversations (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references profiles (id) on delete cascade,
  subject_id uuid not null references subjects (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations (id) on delete cascade,
  role text not null check (role in ('student', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

alter table conversations enable row level security;
alter table messages enable row level security;

create policy "conversations are readable by their student"
  on conversations for select
  using (auth.uid() = student_id);

create policy "messages are readable by their conversation's student"
  on messages for select
  using (
    exists (
      select 1 from conversations
      where conversations.id = messages.conversation_id
        and conversations.student_id = auth.uid()
    )
  );
