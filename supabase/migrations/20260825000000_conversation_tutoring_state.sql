-- Adds per-conversation tutoring state (Decision 019) so the pipeline can
-- track whether a student is stuck across turns and escalate from
-- guided-discovery hints to a full explanation, then confirm
-- understanding, instead of hinting indefinitely.
alter table conversations
  add column tutoring_phase text not null default 'guiding'
    check (tutoring_phase in ('guiding', 'confirming')),
  add column struggle_count integer not null default 0,
  add column confirm_count integer not null default 0;
