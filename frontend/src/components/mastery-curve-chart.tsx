"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Point = { date: string; mastered: number };

const SUBJECT_COLOR: Record<string, string> = { math: "var(--gold)", science: "var(--sage)" };
const SUBJECT_LABEL: Record<string, string> = { math: "Math", science: "Science" };
const SUBJECTS = ["math", "science"];

const CHART_W = 640;
const CHART_H = 220;
const PAD_L = 28;
const PAD_R = 16;
const PAD_T = 16;
const PAD_B = 28;

function formatDate(ms: number): string {
  return new Date(ms).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/**
 * Cumulative topics mastered over time, Math vs Science on shared axes --
 * a growth curve comparison, not a per-topic snapshot (that's TopicChart).
 * A step function: each point is the moment a topic's streak first
 * crossed the mastery threshold (backend: get_mastery_curve), so the line
 * only ever goes up, even if a topic's live tier later drops.
 */
export function MasteryCurveChart({ studentId }: { studentId?: string } = {}) {
  const [curves, setCurves] = useState<Record<string, Point[]> | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      const entries = await Promise.all(
        SUBJECTS.map(async (subject) => {
          const endpoint = studentId
            ? `${process.env.NEXT_PUBLIC_API_URL}/guardian/students/${studentId}/mastery-curve?subject=${subject}&grade_band=6`
            : `${process.env.NEXT_PUBLIC_API_URL}/tutor/mastery-curve?subject=${subject}&grade_band=6`;
          const res = await fetch(endpoint, { headers: { Authorization: `Bearer ${session.access_token}` } });
          const data = res.ok ? await res.json() : { points: [] };
          return [subject, data.points as Point[]] as const;
        })
      );
      if (!cancelled) setCurves(Object.fromEntries(entries));
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [studentId]);

  if (!curves) {
    return <p className="text-sm text-ink/45">Loading progress&hellip;</p>;
  }

  const allPoints = Object.values(curves).flat();
  if (allPoints.length === 0) {
    return <p className="text-sm text-ink/50">No topics mastered yet in either subject &mdash; keep going!</p>;
  }

  const allDates = allPoints.map((p) => new Date(p.date).getTime());
  const minDate = Math.min(...allDates);
  const maxDate = Math.max(...allDates);
  const maxCount = Math.max(...allPoints.map((p) => p.mastered), 1);

  const x = (t: number) =>
    maxDate === minDate
      ? PAD_L + (CHART_W - PAD_L - PAD_R) / 2
      : PAD_L + ((t - minDate) / (maxDate - minDate)) * (CHART_W - PAD_L - PAD_R);
  const y = (v: number) => CHART_H - PAD_B - (v / maxCount) * (CHART_H - PAD_T - PAD_B);

  function stepPath(points: Point[]): string {
    if (points.length === 0) return "";
    const firstX = x(new Date(points[0].date).getTime());
    let d = `M ${firstX} ${y(0)} L ${firstX} ${y(points[0].mastered)}`;
    for (let i = 1; i < points.length; i++) {
      const prevValue = points[i - 1].mastered;
      const curX = x(new Date(points[i].date).getTime());
      d += ` L ${curX} ${y(prevValue)} L ${curX} ${y(points[i].mastered)}`;
    }
    d += ` L ${x(maxDate)} ${y(points[points.length - 1].mastered)}`;
    return d;
  }

  return (
    <div>
      <div className="mb-3 flex gap-4 font-mono text-xs text-ink/55">
        {SUBJECTS.map((s) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className="h-[7px] w-[7px] rounded-full" style={{ background: SUBJECT_COLOR[s] }} />
            {SUBJECT_LABEL[s]}
          </span>
        ))}
      </div>
      <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="block h-auto w-full">
        {Array.from({ length: maxCount + 1 }, (_, i) => i).map((v) => (
          <line
            key={v}
            x1={PAD_L}
            y1={y(v)}
            x2={CHART_W - PAD_R}
            y2={y(v)}
            stroke="rgba(28,34,48,0.06)"
            strokeDasharray="2,3"
          />
        ))}
        <text x={2} y={y(maxCount) + 4} fontFamily="var(--font-mono)" fontSize="9" fill="rgba(28,34,48,0.4)">
          {maxCount}
        </text>
        <text x={2} y={y(0) + 4} fontFamily="var(--font-mono)" fontSize="9" fill="rgba(28,34,48,0.4)">
          0
        </text>
        <text x={PAD_L} y={CHART_H - 6} fontFamily="var(--font-mono)" fontSize="9" fill="rgba(28,34,48,0.4)">
          {formatDate(minDate)}
        </text>
        <text
          x={CHART_W - PAD_R}
          y={CHART_H - 6}
          textAnchor="end"
          fontFamily="var(--font-mono)"
          fontSize="9"
          fill="rgba(28,34,48,0.4)"
        >
          {formatDate(maxDate)}
        </text>

        {SUBJECTS.map((subject) => (
          <path
            key={subject}
            d={stepPath(curves[subject] ?? [])}
            fill="none"
            stroke={SUBJECT_COLOR[subject]}
            strokeWidth={2}
            strokeLinejoin="round"
          />
        ))}
        {SUBJECTS.map((subject) =>
          (curves[subject] ?? []).map((p) => (
            <circle
              key={`${subject}-${p.date}-${p.mastered}`}
              cx={x(new Date(p.date).getTime())}
              cy={y(p.mastered)}
              r={3}
              fill={SUBJECT_COLOR[subject]}
            />
          ))
        )}
      </svg>
    </div>
  );
}
