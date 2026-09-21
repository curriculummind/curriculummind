-- Decision 025: in-app guardian/teacher notifications, computed
-- event-driven off decision_traces (Decision 023) with zero new
-- instrumentation. Per Decision 009, guardians never get raw
-- conversation/transcript access -- message is always a pre-rendered,
-- plain-language summary, never the raw question text, the same rule
-- applied here as to conversation data generally.
--
-- Same admin-only write posture as decision_traces: only the backend's
-- own privileged connection ever inserts a row (a BackgroundTask
-- scheduled at the end of /tutor/ask), so there is no insert/update/
-- delete policy for any client role. The one select policy expresses
-- the actual privacy boundary: a guardian (teacher today, parent later
-- -- guardian_links is already the schema's generic term for both) may
-- read a student's notifications only while their guardian_links row
-- is 'active', not merely because one exists historically -- a revoked
-- link must not go on leaking ongoing alerts.
create table notifications (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references profiles (id) on delete cascade,
  category text not null check (
    category in ('mastery_milestone', 'repeated_struggle', 'assignment_pattern', 'sensitive_topic')
  ),
  message text not null,
  created_at timestamptz not null default now()
);

alter table notifications enable row level security;

create policy "notifications are readable by an active guardian"
  on notifications for select
  using (
    exists (
      select 1 from guardian_links
      where guardian_links.guardian_id = auth.uid()
        and guardian_links.student_id = notifications.student_id
        and guardian_links.status = 'active'
    )
  );
