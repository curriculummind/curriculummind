"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

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
      <main className="mx-auto max-w-sm p-8">
        <h1 className="text-xl font-semibold">Check your email</h1>
        <p className="mt-2 text-sm text-gray-600">
          We sent a confirmation link to {email}. Confirm it, then log in.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="text-xl font-semibold">Sign up</h1>
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
        <input
          type="text"
          placeholder="Name"
          required
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="rounded border px-3 py-2"
        />
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
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={status === "loading"}
          className="rounded bg-black px-3 py-2 text-white disabled:opacity-50"
        >
          {status === "loading" ? "Creating account..." : "Sign up"}
        </button>
      </form>
      <p className="mt-4 text-sm text-gray-600">
        Already have an account? <a href="/login" className="underline">Log in</a>
      </p>
    </main>
  );
}
