"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Logo } from "@/components/logo";

const SUBJECTS = [
  { slug: "math", label: "Math", blurb: "Ratios, expressions, equations, area, and statistics." },
  { slug: "science", label: "Science", blurb: "Cells, genetics, ecosystems, and the human body." },
];

/** The screen after login: pick a subject, check overall progress, or jump back into whatever's in progress. */
export function HomeClient() {
  const router = useRouter();
  const [lastSubject, setLastSubject] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [linkCode, setLinkCode] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;
      const headers = { Authorization: `Bearer ${session.access_token}` };

      const [lastSubjectRes, profileRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/tutor/last-subject`, { headers }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/profile/me`, { headers }),
      ]);
      if (cancelled) return;
      if (lastSubjectRes.ok) {
        const data = await lastSubjectRes.json();
        setLastSubject(data.subject);
      }
      if (profileRes.ok) {
        const profile = await profileRes.json();
        setLinkCode(profile.student_link_code ?? null);
      }
      setLoading(false);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  const lastSubjectLabel = SUBJECTS.find((s) => s.slug === lastSubject)?.label;

  return (
    <main className="mx-auto flex min-h-full max-w-3xl flex-col px-6 py-10">
      <div className="mb-10 flex items-center justify-between">
        <Logo />
        <button onClick={handleLogout} className="text-sm text-ink/55 underline underline-offset-2 hover:text-ink">
          Log out
        </button>
      </div>

      {!loading && lastSubject && (
        <a
          href={`/chat/${lastSubject}`}
          className="mb-8 flex items-center justify-between rounded-lg border border-gold/35 bg-gold/8 px-6 py-5 transition hover:bg-gold/12"
        >
          <div>
            <span className="mb-1 block font-mono text-xs tracking-[0.08em] text-gold uppercase">
              Continue where you left off
            </span>
            <span className="font-display text-lg font-medium text-ink">{lastSubjectLabel}</span>
          </div>
          <span aria-hidden="true" className="text-xl text-gold">
            &rarr;
          </span>
        </a>
      )}

      <section className="mb-10">
        <h2 className="mb-4 font-mono text-xs tracking-[0.1em] text-ink/50 uppercase">Curriculum</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {SUBJECTS.map((s) => (
            <a
              key={s.slug}
              href={`/chat/${s.slug}`}
              className="rounded-lg border border-rule bg-paper-2 p-6 transition hover:border-gold/40 hover:shadow-[0_18px_40px_-28px_rgba(28,34,48,0.3)]"
            >
              <h3 className="mb-1.5 font-display text-xl font-medium text-ink">{s.label}</h3>
              <p className="text-sm leading-relaxed text-ink/60">{s.blurb}</p>
            </a>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-4 font-mono text-xs tracking-[0.1em] text-ink/50 uppercase">Progress</h2>
        <a
          href="/progress"
          className="flex items-center justify-between rounded-lg border border-rule bg-paper-2 p-6 transition hover:border-gold/40 hover:shadow-[0_18px_40px_-28px_rgba(28,34,48,0.3)]"
        >
          <div>
            <h3 className="mb-1.5 font-display text-xl font-medium text-ink">Progress Dashboard</h3>
            <p className="text-sm leading-relaxed text-ink/60">
              A mastery overview across both Math and Science, topic by topic.
            </p>
          </div>
          <span aria-hidden="true" className="text-xl text-ink/40">
            &rarr;
          </span>
        </a>
      </section>

      {linkCode && (
        <p className="mt-10 text-center text-sm text-ink/50">
          Want a parent to see your progress?{" "}
          <span className="font-mono text-ink/70">
            Share this code: <span className="font-semibold text-ink">{linkCode}</span>
          </span>
        </p>
      )}
    </main>
  );
}
