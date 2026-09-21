"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuthShell } from "@/components/auth-shell";

/**
 * Sign-up form: creates a Supabase Auth user, then a matching backend
 * profile. Grade is fixed to 6 -- the only grade band with content
 * ingested so far. A student must redeem a teacher's class code to
 * finish setup (Decision 024) -- parent/guardian linking is deferred.
 */
export default function SignupPage() {
  const router = useRouter();
  const [role, setRole] = useState<"student" | "teacher">("student");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [classCode, setClassCode] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "check-email" | "error">("idle");
  const [error, setError] = useState("");
  const [classCodeError, setClassCodeError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setError("");
    setClassCodeError("");

    const profileFields = {
      role,
      display_name: displayName,
      grade_level: 6,
      class_code: role === "student" ? classCode.trim().toUpperCase() : undefined,
    };

    const supabase = createClient();
    // user_metadata carries these fields through the email-confirmation
    // round trip, so the login page's deferred profile-creation
    // fallback (used when a user confirms and signs in later, rather
    // than having an active session right after signUp) knows the
    // role/class_code the user actually chose instead of guessing.
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: { data: profileFields },
    });

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
      body: JSON.stringify(profileFields),
    });

    if (!response.ok) {
      if (response.status === 400) {
        const body = await response.json().catch(() => null);
        setClassCodeError(body?.detail ?? "That class code doesn't match a teacher.");
        setStatus("error");
        return;
      }
      setError("Account created, but profile setup failed. Try logging in.");
      setStatus("error");
      return;
    }

    const profile = await response.json();
    router.push(profile.role === "teacher" ? "/teacher" : "/home");
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
            I am a
          </label>
          <div className="grid grid-cols-2 gap-2">
            {(["student", "teacher"] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className={`rounded border px-3.5 py-3 text-sm font-medium capitalize transition ${
                  role === r ? "border-gold bg-ink text-paper" : "border-rule bg-paper-2 text-ink/70 hover:border-gold/50"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
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
        {role === "student" && (
          <div>
            <label className="mb-[7px] block font-mono text-[0.68rem] tracking-[0.06em] text-ink/50 uppercase">
              Class code
            </label>
            <input
              type="text"
              placeholder="From your teacher"
              required
              value={classCode}
              onChange={(e) => setClassCode(e.target.value)}
              className="w-full rounded border border-rule bg-paper-2 px-3.5 py-3 uppercase text-ink placeholder:text-ink/30 placeholder:normal-case focus:border-gold focus:ring-2 focus:ring-gold/25 focus:outline-none"
            />
            {classCodeError && <p className="mt-1.5 text-sm text-red-600">{classCodeError}</p>}
          </div>
        )}
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
