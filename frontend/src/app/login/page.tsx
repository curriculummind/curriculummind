"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Logo } from "@/components/logo";

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
    <main className="flex min-h-full flex-col items-center justify-center px-6 py-16">
      <div className="mb-10">
        <Logo />
      </div>
      <div className="w-full max-w-sm rounded-lg border border-rule bg-paper-2 p-8 shadow-[0_18px_40px_-24px_rgba(28,34,48,0.25)]">
        <h1 className="font-display text-2xl font-medium text-ink">Log in</h1>
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
          <input
            type="email"
            placeholder="Email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded border border-rule bg-paper px-3 py-2 text-ink placeholder:text-ink/40 focus:outline-none focus:ring-1 focus:ring-gold"
          />
          <input
            type="password"
            placeholder="Password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded border border-rule bg-paper px-3 py-2 text-ink placeholder:text-ink/40 focus:outline-none focus:ring-1 focus:ring-gold"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="rounded bg-ink px-3 py-2 font-medium text-paper transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Logging in..." : "Log in"}
          </button>
        </form>
      </div>
      <p className="mt-6 text-sm text-ink/60">
        No account yet?{" "}
        <a href="/signup" className="font-medium text-gold underline underline-offset-2">
          Sign up
        </a>
      </p>
    </main>
  );
}
