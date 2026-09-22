-- Decision 027: real curriculum diagrams shown inline in chat, for
-- science topics only (the CK-12/LibreTexts source material has
-- genuine labeled diagrams; the EngageNY math PDFs do not -- confirmed
-- by direct inspection, not assumed).
--
-- Attribution lives at the resource level, not the chunk level.
-- Science ingestion aggregates many CK-12 lesson pages into one
-- curriculum_resources row per concept, and chunk_text() retains no
-- page-boundary metadata per chunk -- retrofitting an exact chunk-to-
-- page mapping onto existing document_chunks rows would be fragile
-- (a silent misattribution is worse than a coarser but honest
-- granularity), and re-ingesting fresh would orphan
-- decision_traces.evidence_chunk_ids, which joins through
-- document_chunks.id for the mastery-tier computation. This table
-- links an image to the resource and the specific lesson page it came
-- from, touching no existing row.
--
-- Same RLS posture as curriculum_resources/document_chunks: readable
-- by any authenticated user, writable only by the backend's own
-- privileged connection (the backfill script), per Decision 010.
create table resource_images (
  id uuid primary key default gen_random_uuid(),
  resource_id uuid not null references curriculum_resources (id) on delete cascade,
  source_page_path text not null,
  source_page_title text not null,
  image_url text not null,
  public_url text not null,
  caption text not null,
  license text not null,
  attribution text not null,
  created_at timestamptz not null default now(),
  unique (resource_id, source_page_path)
);

alter table resource_images enable row level security;

create policy "curriculum content is readable by any authenticated user"
  on resource_images for select
  to authenticated
  using (true);
