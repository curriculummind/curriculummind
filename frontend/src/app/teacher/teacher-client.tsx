"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Logo } from "@/components/logo";
import { MasteryCurveChart } from "@/components/mastery-curve-chart";
import { TopicChart } from "@/components/topic-chart";

type Tier = "mastery" | "learning" | "needs-practice";

type RosterStudent = {
  student_id: string;
  display_name: string;
  subject_tiers: Record<string, Tier | null>;
  needs_attention: boolean;
  last_active: string | null;
};

type Notification = {
  id: string;
  student_id: string;
  student_display_name: string;
  category: string;
  message: string;
  created_at: string;
};

const TIER_COLOR: Record<Tier, string> = {
  mastery: "var(--sage)",
  learning: "var(--gold)",
  "needs-practice": "var(--clay)",
};

const CATEGORY_ICON: Record<string, string> = {
  mastery_milestone: "★",
  repeated_struggle: "•",
  assignment_pattern: "▤",
  sensitive_topic: "◉",
};

const SUBJECTS = ["math", "science"];
const SUBJECT_LABEL: Record<string, string> = { math: "Math", science: "Science" };

function formatRelative(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diffMs / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/**
 * The teacher's roster: every linked student, a per-subject mastery-tier
 * summary each, and a notification feed -- the guardian side of the
 * same mastery data students see about themselves (Decision 025).
 */
export function TeacherClient({ classCode }: { classCode: string | null }) {
  const router = useRouter();
  const [roster, setRoster] = useState<RosterStudent[] | null>(null);
  const [notifications, setNotifications] = useState<Notification[] | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [bellOpen, setBellOpen] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.push("/login");
        return;
      }
      const headers = { Authorization: `Bearer ${session.access_token}` };

      const [rosterRes, notifRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/guardian/roster`, { headers }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/guardian/notifications`, { headers }),
      ]);
      if (cancelled) return;
      if (rosterRes.ok) setRoster((await rosterRes.json()).students);
      if (notifRes.ok) setNotifications((await notifRes.json()).notifications);
    }
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) setBellOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  const studentCount = roster?.length ?? 0;
  const tierValues = (roster ?? []).flatMap((s) => Object.values(s.subject_tiers)).filter((t): t is Tier => t !== null);
  const avgMastery = tierValues.length ? Math.round((tierValues.filter((t) => t === "mastery").length / tierValues.length) * 100) : 0;
  const needsAttentionCount = (roster ?? []).filter((s) => s.needs_attention).length;

  return (
    <main className="mx-auto flex min-h-full max-w-5xl flex-col px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <Logo />
        <div className="flex items-center gap-4">
          {classCode && (
            <span className="rounded-full border border-gold/35 bg-gold/8 px-3.5 py-1.5 font-mono text-xs tracking-[0.06em] text-gold uppercase">
              Class code &middot; {classCode}
            </span>
          )}
          <div className="relative" ref={bellRef}>
            <button
              onClick={() => setBellOpen((v) => !v)}
              aria-label="Notifications"
              className="relative flex h-9 w-9 items-center justify-center rounded-full border border-rule bg-paper-2 text-ink hover:bg-paper-3"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              {notifications && notifications.length > 0 && (
                <span className="absolute top-1.5 right-2 h-[7px] w-[7px] rounded-full border border-paper-2 bg-clay" />
              )}
            </button>
            {bellOpen && (
              <div className="absolute top-11 right-0 z-20 w-96 rounded-lg border border-rule bg-paper-2 p-1.5 shadow-[0_24px_48px_-24px_rgba(28,34,48,0.35)]">
                <div className="flex items-center justify-between px-3 py-2.5">
                  <h3 className="font-display text-base font-medium text-ink">Notifications</h3>
                  <span className="font-mono text-xs text-ink/45">{notifications?.length ?? 0}</span>
                </div>
                {notifications && notifications.length === 0 && (
                  <p className="px-3 pb-3 text-sm text-ink/50">Nothing yet.</p>
                )}
                {(notifications ?? []).map((n) => (
                  <div key={n.id} className="flex gap-2.5 rounded-md px-3 py-2.5 hover:bg-paper-3">
                    <span className="mt-0.5 text-sm text-ink/55">{CATEGORY_ICON[n.category] ?? "•"}</span>
                    <div>
                      <p className="text-[0.82rem] leading-relaxed text-ink">
                        {n.message}
                      </p>
                      <div className="mt-0.5 font-mono text-[0.65rem] text-ink/40">{formatRelative(n.created_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <button onClick={handleLogout} className="text-sm text-ink/55 underline underline-offset-2 hover:text-ink">
            Log out
          </button>
        </div>
      </div>

      <h1 className="mb-1 font-display text-2xl font-medium text-ink">Your class</h1>
      <p className="mb-8 text-sm text-ink/60">Every linked student, plotted against their mastery tier.</p>

      <div className="mb-8 grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-rule bg-paper-2 p-5">
          <div className="font-display text-2xl font-medium text-ink">{studentCount}</div>
          <div className="mt-1 font-mono text-xs text-ink/50 uppercase">Students</div>
        </div>
        <div className="rounded-lg border border-rule bg-paper-2 p-5">
          <div className="font-display text-2xl font-medium text-ink">{avgMastery}%</div>
          <div className="mt-1 font-mono text-xs text-ink/50 uppercase">Avg. topics mastered</div>
        </div>
        <div className="rounded-lg border border-rule bg-paper-2 p-5">
          <div className="font-display text-2xl font-medium text-ink">{needsAttentionCount}</div>
          <div className="mt-1 font-mono text-xs text-ink/50 uppercase">Need attention</div>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-rule bg-paper-2">
        {roster === null && <p className="p-6 text-sm text-ink/45">Loading roster&hellip;</p>}
        {roster && roster.length === 0 && (
          <p className="p-6 text-sm text-ink/50">No students have joined your class yet. Share your class code above.</p>
        )}
        {roster && roster.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-rule text-left font-mono text-[0.66rem] tracking-[0.05em] text-ink/45 uppercase">
                <th className="px-5 py-3 font-medium">Student</th>
                {SUBJECTS.map((s) => (
                  <th key={s} className="px-5 py-3 font-medium">
                    {SUBJECT_LABEL[s]}
                  </th>
                ))}
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Last active</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {roster.map((student) => (
                <Fragment key={student.student_id}>
                  <tr
                    className="cursor-pointer border-b border-rule hover:bg-paper-3"
                    onClick={() => setExpandedId(expandedId === student.student_id ? null : student.student_id)}
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-paper-3 font-display text-xs text-ink">
                          {student.display_name[0]}
                        </div>
                        <span className="font-medium text-ink">{student.display_name}</span>
                      </div>
                    </td>
                    {SUBJECTS.map((s) => {
                      const tier = student.subject_tiers[s];
                      return (
                        <td key={s} className="px-5 py-3.5">
                          <span
                            className="inline-block h-2.5 w-2.5 rounded-full"
                            style={{ background: tier ? TIER_COLOR[tier] : "rgba(28,34,48,0.2)" }}
                            title={tier ?? "not started"}
                          />
                        </td>
                      );
                    })}
                    <td className="px-5 py-3.5">
                      {student.needs_attention ? (
                        <span className="rounded-full bg-clay/12 px-2.5 py-1 font-mono text-[0.66rem] text-clay">
                          Needs attention
                        </span>
                      ) : (
                        <span className="rounded-full bg-sage/10 px-2.5 py-1 font-mono text-[0.66rem] text-sage">On track</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-xs text-ink/50">{formatRelative(student.last_active)}</td>
                    <td className="px-5 py-3.5 text-right text-ink/40">{expandedId === student.student_id ? "⌄" : "⌃"}</td>
                  </tr>
                  {expandedId === student.student_id && (
                    <tr className="border-b border-rule bg-paper-3">
                      <td colSpan={5} className="p-5">
                        <div className="rounded-lg border border-rule bg-paper-2 p-5">
                          <p className="mb-4 font-mono text-xs tracking-[0.07em] text-ink/50 uppercase">Growth over time</p>
                          <MasteryCurveChart studentId={student.student_id} />
                          <div className="mt-6 grid gap-5 md:grid-cols-2">
                            {SUBJECTS.map((subject) => (
                              <div key={subject} className="overflow-hidden rounded-lg border border-rule">
                                <div className="border-b border-rule bg-paper-3 px-4 py-2.5 font-display text-sm font-medium text-ink">
                                  {SUBJECT_LABEL[subject]}
                                </div>
                                <div className="max-h-72 overflow-y-auto">
                                  <TopicChart subject={subject} studentId={student.student_id} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
