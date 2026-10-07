"use client";

import { useState } from "react";

/**
 * Public, no-login interest capture (Decision 034) -- for a parent or
 * teacher not ready to create a full account yet. Posts straight to
 * the backend; there's no Supabase Auth session to attach here.
 */
export function WaitlistForm() {
  const [email, setEmail] = useState("");
  const [interest, setInterest] = useState<"parent" | "teacher">("parent");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, interest }),
      });
      setStatus(res.ok ? "done" : "error");
    } catch {
      setStatus("error");
    }
  }

  if (status === "done") {
    return <p className="text-sm font-medium text-sage">You&rsquo;re on the list &mdash; we&rsquo;ll be in touch.</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="flex rounded-sm border border-rule bg-paper-2 p-1 font-mono text-xs">
        {(["parent", "teacher"] as const).map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setInterest(r)}
            className={`rounded-sm px-3 py-1.5 capitalize transition ${
              interest === r ? "bg-ink text-paper" : "text-ink/60 hover:text-ink"
            }`}
          >
            {r}
          </button>
        ))}
      </div>
      <input
        type="email"
        required
        placeholder="you@email.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="min-w-0 flex-1 rounded-sm border border-rule bg-paper-2 px-3.5 py-2.5 text-sm text-ink placeholder:text-ink/30 focus:border-gold focus:ring-2 focus:ring-gold/25 focus:outline-none"
      />
      <button
        type="submit"
        disabled={status === "loading"}
        className="rounded-sm bg-gold px-5 py-2.5 text-sm font-semibold whitespace-nowrap text-paper transition hover:opacity-90 disabled:opacity-50"
      >
        {status === "loading" ? "Joining..." : "Join the waitlist"}
      </button>
      {status === "error" && <p className="text-sm text-red-600">Something went wrong. Try again.</p>}
    </form>
  );
}
