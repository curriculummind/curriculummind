"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

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
    <main className="mx-auto max-w-sm p-8">
      <h1 className="text-xl font-semibold">Log in</h1>
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
        <input
          type="email"
          placeholder="Email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border px-3 py-2"
        />
        <input
          type="password"
          placeholder="Password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-black px-3 py-2 text-white disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-gray-600">
        No account yet? <a href="/signup" className="underline">Sign up</a>
      </p>
    </main>
  );
}
