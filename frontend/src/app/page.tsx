import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Logo } from "@/components/logo";
import { HeroGraph } from "@/components/hero-graph";

const PRINCIPLES = [
  {
    num: "01 · RETRIEVE",
    title: "Grounded, not generated",
    body: "Every answer traces back to a real page of real curriculum, mechanically extracted, never paraphrased by a model.",
  },
  {
    num: "02 · GUIDE",
    title: "Discovery over delivery",
    body: "A short anchor, then one genuine question. The tutor withholds the answer on purpose; that's the whole method.",
  },
  {
    num: "03 · ESCALATE",
    title: "Struggle has a limit",
    body: "Three honest attempts, then a full explanation, followed by questions that confirm it actually landed.",
  },
];

function DocIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 4h16v16H4z" />
      <path d="M8 8h8M8 12h8M8 16h5" />
    </svg>
  );
}

function StudentBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[82%] rounded-tl-[10px] rounded-tr-[10px] rounded-br-[2px] rounded-bl-[10px] bg-paper-3 px-[18px] py-[15px] text-base leading-relaxed text-ink">
        {children}
      </div>
    </div>
  );
}

/** Sends signed-in students straight to the chat page; everyone else sees the marketing landing page. */
export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) redirect("/chat");

  return (
    <div className="flex min-h-full flex-col">
      <header className="mx-auto flex w-full max-w-[1180px] items-center justify-between px-8 py-7">
        <Logo />
        <nav className="hidden items-center gap-9 text-sm text-ink/65 lg:flex">
          <a href="#how-it-teaches" className="hover:text-ink">
            How it teaches
          </a>
          <span>Curriculum</span>
          <span>For schools</span>
        </nav>
        <a
          href="/login"
          className="rounded-sm bg-gold px-5 py-[10px] text-sm font-semibold text-paper transition hover:opacity-90"
        >
          Start a session
        </a>
      </header>

      <section className="relative mx-auto w-full max-w-[1180px] px-8 pt-16 pb-24">
        <HeroGraph />
        <span className="inline-flex items-center gap-[9px] rounded-sm border border-gold/35 px-[14px] py-[7px] font-mono text-xs tracking-[0.14em] text-gold uppercase">
          <span className="h-[6px] w-[6px] rounded-full bg-gold shadow-[0_0_8px_rgba(201,143,31,0.55)]" />
          Grades 6&ndash;12
        </span>
        <h1 className="mt-7 mb-[26px] max-w-[21ch] text-balance font-display text-[clamp(2.2rem,4.6vw,3.9rem)] leading-[1.08] font-medium tracking-tight text-ink">
          Adaptive Learning Intelligence for <em className="text-gold italic">Modern Education.</em>
        </h1>
        <p className="mb-[38px] max-w-[36ch] text-base leading-relaxed text-ink/70">
          CurriculumMind never hands over the solution. It anchors every response in real, licensed
          curriculum text, then asks the one question that moves your thinking forward, the way a good
          teacher would, not the way a search engine does.
        </p>
        <div className="mb-14 flex items-center gap-[22px]">
          <a
            href="/login"
            className="inline-flex items-center gap-[10px] rounded-sm bg-ink px-7 py-[15px] text-base font-semibold text-paper transition hover:opacity-90"
          >
            Start a session &rarr;
          </a>
          <a href="#demo" className="border-b border-ink/30 py-[15px] text-base font-medium text-ink">
            See how it teaches
          </a>
        </div>
        <div className="flex items-center gap-4 font-mono text-xs text-ink/50">
          <span>Grounded in</span>
          <span className="flex gap-2">
            <span className="rounded-sm border border-ink/20 px-[9px] py-1">Common Core</span>
            <span className="rounded-sm border border-ink/20 px-[9px] py-1">CK-12</span>
          </span>
        </div>
      </section>

      <section id="how-it-teaches" className="border-y border-rule py-[54px]">
        <div className="mx-auto grid max-w-[1180px] gap-11 px-8 md:grid-cols-3">
          {PRINCIPLES.map((p) => (
            <div key={p.num}>
              <span className="mb-3.5 block font-mono text-xs tracking-[0.1em] text-gold">{p.num}</span>
              <h3 className="mb-2.5 font-display text-[1.32rem] font-medium text-ink">{p.title}</h3>
              <p className="text-[0.95rem] leading-relaxed text-ink/60">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="demo" className="mx-auto w-full max-w-[1180px] px-8 pt-24 pb-[110px]">
        <div className="mb-[52px] max-w-[52ch]">
          <span className="mb-[22px] inline-flex items-center gap-[9px] rounded-sm border border-gold/35 px-[14px] py-[7px] font-mono text-xs tracking-[0.14em] text-gold uppercase">
            <span className="h-[6px] w-[6px] rounded-full bg-gold" />
            Inside a session
          </span>
          <h2 className="mb-4 text-balance font-display text-[clamp(1.8rem,3.2vw,2.5rem)] leading-[1.15] font-medium text-ink">
            Watch it hold the line on a ratio problem.
          </h2>
          <p className="leading-relaxed text-ink/60">
            A real Grade 6 exchange, styled the way the product should feel: not a chat bubble template, a
            page in a shared notebook.
          </p>
        </div>

        <div className="max-w-[780px] overflow-hidden rounded-md border border-rule bg-paper-2 shadow-[0_18px_40px_-24px_rgba(28,34,48,0.25)]">
          <div className="flex items-center justify-between border-b border-rule px-[26px] py-5">
            <div className="flex items-center gap-3">
              <div className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-gradient-to-br from-gold to-ink font-display text-sm font-semibold text-paper">
                M
              </div>
              <div>
                <strong className="block text-sm font-semibold text-ink">Math &middot; Ratios</strong>
                <span className="font-mono text-xs text-ink/50">6.RP.A.1 &middot; Grade 6</span>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-sage/35 px-3 py-1.5 font-mono text-xs tracking-[0.06em] text-sage uppercase">
              <span className="h-1.5 w-1.5 rounded-full bg-sage motion-safe:animate-pulse" />
              Guiding
            </div>
          </div>

          <div className="flex flex-col gap-[22px] px-[26px] pt-[30px] pb-[34px]">
            <StudentBubble>
              At the malt shop, the ratio of hotdogs to hamburgers sold was 6:8. If they sold 24
              hamburgers, how many hotdogs?
            </StudentBubble>

            <div>
              <span className="mb-3 inline-flex items-center gap-1.5 rounded-sm border border-rule px-[9px] py-1 font-mono text-[0.68rem] text-ink/55">
                <DocIcon /> Common Core &middot; 6.RP.A.1
              </span>
              <p className="mb-3 text-ink/90">For every 8 hamburgers, there are 6 hotdogs, that's your ratio, 6 to 8.</p>
              <p className="border-l-2 border-gold pl-4 font-display text-lg leading-relaxed text-gold italic">
                24 is how many groups of 8?
              </p>
            </div>

            <StudentBubble>24 minus 8 is 16, so 16 hotdogs?</StudentBubble>

            <div>
              <p className="mb-3 text-ink/90">Not quite. You need groups of 8, not subtraction.</p>
              <p className="border-l-2 border-gold pl-4 font-display text-lg leading-relaxed text-gold italic">
                How many times does 8 fit into 24?
              </p>
            </div>

            <StudentBubble>8 times 3 is 24, so 3 groups.</StudentBubble>

            <div className="flex items-start gap-3 rounded-md border border-sage/28 bg-sage/8 px-[18px] py-4 text-sm leading-relaxed text-ink/85">
              <div>
                <strong className="mb-1.5 block font-mono text-[0.68rem] tracking-[0.08em] text-sage uppercase">
                  Confirmed &middot; wrap-up
                </strong>
                Exactly. 3 groups of 6 hotdogs is 18. You scaled the ratio correctly. Ready for a new one?
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3.5 border-t border-rule px-[26px] py-[18px]">
            <div className="flex-1 rounded border border-rule bg-paper px-3.5 py-3 text-sm text-ink/40">
              Ask a question, or answer the one above&hellip;
            </div>
            <div className="rounded bg-ink px-5 py-3 text-sm font-semibold whitespace-nowrap text-paper">Ask</div>
          </div>
        </div>
      </section>

      <footer className="mx-auto flex w-full max-w-[1180px] items-center justify-between border-t border-rule px-8 pt-10 pb-[60px] font-mono text-xs text-ink/45">
        <span>CurriculumMind &middot; A student&rsquo;s thinking, rendered as it happens</span>
        <span>&copy; 2026 CurriculumMind</span>
      </footer>
    </div>
  );
}
