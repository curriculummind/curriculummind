import { Logo } from "@/components/logo";

/**
 * Split-screen shell shared by login and signup: an editorial panel carrying
 * real brand and demo content (echoing the landing page) paired with the
 * actual form, so auth doesn't feel disconnected from the rest of the site.
 */
export function AuthShell({
  eyebrow,
  heading,
  lede,
  children,
}: {
  eyebrow: string;
  heading: string;
  lede: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden items-center justify-center border-r border-rule bg-paper-3 px-14 py-10 lg:flex">
        <div className="flex w-full max-w-[420px] flex-col gap-12">
          <Logo />

          <div>
            <span className="mb-[22px] inline-flex items-center gap-2 rounded-sm border border-gold/35 px-3.5 py-1.5 font-mono text-xs tracking-[0.14em] text-gold uppercase">
              <span className="h-1.5 w-1.5 rounded-full bg-gold" />
              Grades 6&ndash;12
            </span>
            <h1 className="mb-[18px] text-balance font-display text-[2.1rem] leading-[1.18] font-medium text-ink">
              Pick up right where your <em className="text-gold italic">thinking</em> left off.
            </h1>
            <p className="text-[0.98rem] leading-relaxed text-ink/62">
              Every session anchors in real curriculum text, then asks the one question that moves you
              forward.
            </p>

            <div className="mt-7 rounded-lg border border-rule bg-paper-2 px-[22px] py-5 shadow-[0_18px_40px_-28px_rgba(28,34,48,0.25)]">
              <span className="mb-3 inline-flex items-center rounded-sm border border-rule px-[9px] py-1 font-mono text-[0.66rem] text-ink/55">
                Common Core &middot; 6.RP.A.1
              </span>
              <p className="mb-2.5 text-[0.92rem] leading-relaxed text-ink/90">
                For every 8 hamburgers, there are 6 hotdogs, that's your ratio, 6 to 8.
              </p>
              <p className="border-l-2 border-gold pl-3.5 font-display text-base leading-relaxed text-gold italic">
                24 is how many groups of 8?
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3.5 font-mono text-xs text-ink/50">
            <span>Grounded in</span>
            <span className="flex gap-2">
              <span className="rounded-sm border border-ink/20 px-[9px] py-1">Common Core</span>
              <span className="rounded-sm border border-ink/20 px-[9px] py-1">CK-12</span>
            </span>
          </div>
        </div>
      </div>

      <div className="flex flex-col px-6 py-10 lg:px-14">
        <a href="/" className="w-fit text-sm text-ink/55 hover:text-ink">
          &larr; Back to home
        </a>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center">
          <span className="mb-3.5 font-mono text-xs tracking-[0.14em] text-sage uppercase">{eyebrow}</span>
          <h2 className="mb-2 font-display text-3xl font-medium text-ink">{heading}</h2>
          <p className="mb-8 text-[0.94rem] leading-relaxed text-ink/60">{lede}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
