"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuthShell } from "@/components/auth-shell";

/** Login form: signs in with Supabase Auth and redirects to the chat page. */
export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const supabase = createClient();
    const { data, error: signInError } = await supabase.auth.signInWithPassword({ email, password });

    if (signInError) {
      setError(signInError.message);
      setLoading(false);
      return;
    }

    // Covers the case where signup required email confirmation, so the
    // profile was never created at signup time -- this is the first
    // point a confirmed user has a usable session.
    const token = data.session.access_token;
    const existing = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/profile/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (existing.status === 404) {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ role: "student", display_name: email.split("@")[0], grade_level: 6 }),
      });
    }

    router.push("/chat");
    router.refresh();
  }

  return (
    <AuthShell eyebrow="Welcome back" heading="Log in" lede="Continue a session or start a new one.">
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
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
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border border-rule bg-paper-2 px-3.5 py-3 text-ink placeholder:text-ink/30 focus:border-gold focus:ring-2 focus:ring-gold/25 focus:outline-none"
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="mt-1 rounded bg-ink px-3 py-3.5 font-semibold text-paper transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-ink/60">
        No account yet?{" "}
        <a href="/signup" className="font-semibold text-gold underline underline-offset-2">
          Sign up
        </a>
      </p>
    </AuthShell>
  );
}
