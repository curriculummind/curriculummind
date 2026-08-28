"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Logo } from "@/components/logo";

type Tier = "mastery" | "learning" | "needs-practice";
type Topic = { resource_id: string; letter: string | null; name: string; tier: Tier | null };
type Module = { concept_id: string; name: string; module_number: number | null; topics: Topic[] };

const TIER_COLOR: Record<Tier, string> = {
  mastery: "var(--sage)",
  learning: "var(--gold)",
  "needs-practice": "var(--clay)",
};
const TIER_SLOT: Record<Tier, number> = { "needs-practice": 0, learning: 1, mastery: 2 };

const CHART_W = 320;
const LABEL_W = 138;
const RIGHT_PAD = 16;
const ROW_H = 22;
const MODULE_HEAD_H = 24;
const TOP_PAD = 8;

function colX(tier: Tier | null) {
  const slot = tier ? TIER_SLOT[tier] + 1 : 0;
  return LABEL_W + ((CHART_W - RIGHT_PAD - LABEL_W) * (slot + 0.5)) / 4;
}

function truncate(text: string, max: number) {
  return text.length > max ? text.slice(0, max - 1) + "…" : text;
}

export type SelectedTopic = { resourceId: string; moduleName: string; topicName: string };

/**
 * Every topic in a subject, plotted against its mastery tier -- an
 * honest per-topic confidence chart, not an activity count. `version`
 * bumps whenever the chat completes a turn so a fresh correct/incorrect
 * answer shows up here without a manual refresh.
 */
export function TopicChart({
  subject,
  onSubjectChange,
  selected,
  onSelectTopic,
  version,
}: {
  subject: string;
  onSubjectChange: (s: string) => void;
  selected: SelectedTopic | null;
  onSelectTopic: (topic: SelectedTopic) => void;
  version: number;
}) {
  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/tutor/progress?subject=${subject}&grade_band=6`,
        { headers: { Authorization: `Bearer ${session.access_token}` } }
      );
      if (!res.ok || cancelled) return;
      const data = await res.json();
      if (!cancelled) {
        setModules(data.modules);
        setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [subject, version]);

  type Row = { y: number; header?: string; topic?: Topic; moduleName?: string };
  const rows: Row[] = [];
  let y = TOP_PAD;
  modules.forEach((m) => {
    rows.push({ y, header: `${m.module_number ? `Module ${m.module_number} · ` : ""}${m.name}` });
    y += MODULE_HEAD_H;
    m.topics.forEach((t) => {
      rows.push({ y, topic: t, moduleName: m.name });
      y += ROW_H;
    });
    y += 6;
  });
  const height = y + 6;

  return (
    <aside className="flex h-screen flex-col border-r border-rule bg-paper-3">
      <div className="border-b border-rule px-5 py-4">
        <div className="mb-4">
          <Logo />
        </div>
        <div className="flex gap-1.5 rounded-md bg-ink/5 p-1">
          {["math", "science"].map((s) => (
            <button
              key={s}
              onClick={() => onSubjectChange(s)}
              className={`flex-1 rounded px-0 py-1.5 text-sm font-medium capitalize transition ${
                subject === s ? "bg-paper-2 text-ink shadow-sm" : "text-ink/55"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <div className="mb-3.5 flex flex-wrap gap-3 border-b border-rule pb-3.5 font-mono text-[0.66rem] text-ink/55">
          <span className="flex items-center gap-1.5">
            <span className="h-[7px] w-[7px] rounded-full bg-ink/30" />
            Not started
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-[7px] w-[7px] rounded-full bg-clay" />
            Needs practice
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-[7px] w-[7px] rounded-full bg-gold" />
            Learning
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-[7px] w-[7px] rounded-full bg-sage" />
            Mastery
          </span>
        </div>

        {loading ? (
          <p className="text-sm text-ink/45">Loading topics&hellip;</p>
        ) : (
          <svg viewBox={`0 0 ${CHART_W} ${height}`} className="block h-auto w-full">
            {[0, 1, 2, 3].map((i) => {
              const x = LABEL_W + ((CHART_W - RIGHT_PAD - LABEL_W) * (i + 0.5)) / 4;
              return (
                <line
                  key={i}
                  x1={x}
                  y1={TOP_PAD}
                  x2={x}
                  y2={height - 6}
                  stroke="rgba(28,34,48,0.08)"
                  strokeDasharray="2,3"
                />
              );
            })}

            {rows.map((row, i) => {
              if (row.header) {
                const text = truncate(row.header.toUpperCase(), 40);
                return (
                  <text
                    key={i}
                    x={0}
                    y={row.y + 16}
                    fontFamily="var(--font-mono)"
                    fontSize="9.5"
                    letterSpacing="0.04em"
                    fill="rgba(28,34,48,0.5)"
                  >
                    <title>{row.header}</title>
                    {text}
                  </text>
                );
              }

              const t = row.topic!;
              const cy = row.y + ROW_H / 2 + 2;
              const dotX = colX(t.tier);
              const color = t.tier ? TIER_COLOR[t.tier] : "rgba(28,34,48,0.3)";
              const fullLabel = `${t.letter ? `${t.letter}. ` : ""}${t.name}`;
              const active = selected?.resourceId === t.resource_id;

              return (
                <g
                  key={t.resource_id}
                  className="cursor-pointer"
                  onClick={() =>
                    onSelectTopic({ resourceId: t.resource_id, moduleName: row.moduleName!, topicName: t.name })
                  }
                >
                  <rect
                    x={0}
                    y={row.y - 1}
                    width={CHART_W}
                    height={ROW_H}
                    fill={active ? "var(--paper-2)" : "transparent"}
                    rx={4}
                  />
                  {active && <rect x={0} y={row.y - 1} width={3} height={ROW_H} fill="var(--gold)" />}
                  <text
                    x={10}
                    y={cy + 3}
                    fontFamily="var(--font-sans)"
                    fontSize="10.5"
                    fontWeight={active ? 600 : 400}
                    fill="var(--ink)"
                  >
                    <title>{fullLabel}</title>
                    {truncate(fullLabel, 24)}
                  </text>
                  <line x1={LABEL_W} y1={cy} x2={dotX} y2={cy} stroke={color} strokeOpacity="0.35" />
                  <circle cx={dotX} cy={cy} r={t.tier ? 4 : 3} fill={color} />
                </g>
              );
            })}
          </svg>
        )}
      </div>

      <div className="border-t border-rule px-5 py-3 font-mono text-xs text-ink/45">Grade 6 &middot; Common Core</div>
    </aside>
  );
}
