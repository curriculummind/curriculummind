-- concept_standards was defined right next to standards in the initial
-- schema migration and got the same "readable by any authenticated
-- user" policy intent, but the `enable row level security` line for it
-- was omitted -- a copy/paste gap, not a deliberate choice. Flagged by
-- Supabase's Security Advisor as a critical "table publicly accessible"
-- issue: with RLS off, the anon key (public by design, shipped in the
-- frontend bundle) could read, edit, or delete rows directly via the
-- Supabase REST API, bypassing the backend entirely.
--
-- The data itself isn't sensitive (curriculum-standard mappings, no
-- student data), so this matches the exact policy already used on
-- every other curriculum reference table, not a new access model.
alter table concept_standards enable row level security;

create policy "curriculum content is readable by any authenticated user"
  on concept_standards for select to authenticated using (true);
