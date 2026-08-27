"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuthShell } from "@/components/auth-shell";

/** Sign-up form: creates a Supabase Auth user, then a matching backend profile. Grade is fixed to 6 -- the only grade band with content ingested so far. */
export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "check-email" | "error">("idle");
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setError("");

    const supabase = createClient();
    const { data, error: signUpError } = await supabase.auth.signUp({ email, password });

    if (signUpError) {
      setError(signUpError.message);
      setStatus("error");
      return;
    }

    if (!data.session) {
      setStatus("check-email");
      return;
    }

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/profile`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${data.session.access_token}`,
      },
      body: JSON.stringify({ role: "student", display_name: displayName, grade_level: 6 }),
    });

    if (!response.ok) {
      setError("Account created, but profile setup failed. Try logging in.");
      setStatus("error");
      return;
    }

    router.push("/chat");
  }

  if (status === "check-email") {
    return (
      <AuthShell eyebrow="Almost there" heading="Check your email" lede="One last step before your first session.">
        <p className="text-sm leading-relaxed text-ink/70">
          We sent a confirmation link to <span className="font-medium text-ink">{email}</span>. Confirm it,
          then log in.
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell eyebrow="Get started" heading="Sign up" lede="Create an account to start your first session.">
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <div>
          <label className="mb-[7px] block font-mono text-[0.68rem] tracking-[0.06em] text-ink/50 uppercase">
            Name
          </label>
          <input
            type="text"
            placeholder="Your name"
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full rounded border border-rule bg-paper-2 px-3.5 py-3 text-ink placeholder:text-ink/30 focus:border-gold focus:ring-2 focus:ring-gold/25 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-[7px] block font-mono text-[0.68rem] tracking-[0.06em] text-ink/50 uppercase">
            Email
          </label>
          <input
            type="email"
            placeholder="you@school.edu"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded border border-rule bg-paper-2 px-3.5 py-3 text-ink placeholder:text-ink/30 focus:border-gold focus:ring-2 focus:ring-gold/25 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-[7px] block font-mono text-[0.68rem] tracking-[0.06em] text-ink/50 uppercase">
            Password
          </label>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border border-rule bg-paper-2 px-3.5 py-3 text-ink placeholder:text-ink/30 focus:border-gold focus:ring-2 focus:ring-gold/25 focus:outline-none"
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={status === "loading"}
          className="mt-1 rounded bg-ink px-3 py-3.5 font-semibold text-paper transition hover:opacity-90 disabled:opacity-50"
        >
          {status === "loading" ? "Creating account..." : "Sign up"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-ink/60">
        Already have an account?{" "}
        <a href="/login" className="font-semibold text-gold underline underline-offset-2">
          Log in
        </a>
      </p>
    </AuthShell>
  );
}
