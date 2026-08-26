"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Logo } from "@/components/logo";

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
      <main className="flex min-h-full flex-col items-center justify-center px-6 py-16">
        <div className="mb-10">
          <Logo />
        </div>
        <div className="w-full max-w-sm rounded-lg border border-rule bg-paper-2 p-8 text-center shadow-[0_18px_40px_-24px_rgba(28,34,48,0.25)]">
          <h1 className="font-display text-2xl font-medium text-ink">Check your email</h1>
          <p className="mt-3 text-sm text-ink/65">
            We sent a confirmation link to {email}. Confirm it, then log in.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-full flex-col items-center justify-center px-6 py-16">
      <div className="mb-10">
        <Logo />
      </div>
      <div className="w-full max-w-sm rounded-lg border border-rule bg-paper-2 p-8 shadow-[0_18px_40px_-24px_rgba(28,34,48,0.25)]">
        <h1 className="font-display text-2xl font-medium text-ink">Sign up</h1>
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
          <input
            type="text"
            placeholder="Name"
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="rounded border border-rule bg-paper px-3 py-2 text-ink placeholder:text-ink/40 focus:outline-none focus:ring-1 focus:ring-gold"
          />
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
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded border border-rule bg-paper px-3 py-2 text-ink placeholder:text-ink/40 focus:outline-none focus:ring-1 focus:ring-gold"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={status === "loading"}
            className="rounded bg-ink px-3 py-2 font-medium text-paper transition hover:opacity-90 disabled:opacity-50"
          >
            {status === "loading" ? "Creating account..." : "Sign up"}
          </button>
        </form>
      </div>
      <p className="mt-6 text-sm text-ink/60">
        Already have an account?{" "}
        <a href="/login" className="font-medium text-gold underline underline-offset-2">
          Log in
        </a>
      </p>
    </main>
  );
}
