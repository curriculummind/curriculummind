"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Logo } from "@/components/logo";

type ChatMessage = {
  role: "student" | "assistant";
  content: string;
};

const ACCEPTED_UPLOAD_TYPES =
  "image/jpeg,image/png,image/webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

/**
 * M0 chat UI with real conversation persistence: messages accumulate
 * into a thread, and the conversation id returned by the backend is
 * reused on every subsequent question so follow-ups actually continue
 * the same dialogue instead of starting fresh each time.
 */
export function ChatClient() {
  const router = useRouter();
  const [subject, setSubject] = useState("math");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [tutoringPhase, setTutoringPhase] = useState("guiding");
  const [loading, setLoading] = useState(false);
  const [attaching, setAttaching] = useState(false);
  const [attachError, setAttachError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    setAttachError(null);
    setAttaching(true);

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      router.push("/login");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/tutor/transcribe`, {
      method: "POST",
      headers: { Authorization: `Bearer ${session.access_token}` },
      body: formData,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setAttachError(body?.detail ?? "Could not read that file. Try a clearer photo or a different file.");
      setAttaching(false);
      return;
    }

    const { text } = await res.json();
    setQuestion(text);
    setAttaching(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const asked = question.trim();
    if (!asked) return;

    setLoading(true);
    setQuestion("");
    setMessages((prev) => [...prev, { role: "student", content: asked }]);

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      router.push("/login");
      return;
    }

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/tutor/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        question: asked,
        subject,
        grade_band: "6",
        conversation_id: conversationId,
      }),
    });

    const newConversationId = res.headers.get("X-Conversation-Id");
    if (newConversationId) {
      setConversationId(newConversationId);
    }

    const newPhase = res.headers.get("X-Tutoring-Phase");
    if (newPhase) {
      setTutoringPhase(newPhase);
    }

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    const reader = res.body?.getReader();
    const decoder = new TextDecoder();

    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: next[next.length - 1].content + chunk,
        };
        return next;
      });
    }

    setLoading(false);
  }

  function handleSubjectChange(next: string) {
    setSubject(next);
    setMessages([]);
    setConversationId(null);
    setTutoringPhase("guiding");
  }

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  const subjectLabel = subject === "math" ? "Math" : "Science";
  const phaseLabel = tutoringPhase === "confirming" ? "Confirming" : "Guiding";

  return (
    <main className="mx-auto flex min-h-full max-w-2xl flex-col px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <Logo />
        <button onClick={handleLogout} className="text-sm text-ink/55 underline underline-offset-2 hover:text-ink">
          Log out
        </button>
      </div>

      <div className="overflow-hidden rounded-lg border border-rule bg-paper-2 shadow-[0_18px_40px_-24px_rgba(28,34,48,0.25)]">
        <div className="flex items-center justify-between border-b border-rule px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-gold to-[color-mix(in_srgb,var(--gold),black_35%)] font-display text-sm font-semibold text-paper">
              {subjectLabel[0]}
            </div>
            <div>
              <select
                value={subject}
                onChange={(e) => handleSubjectChange(e.target.value)}
                className="-ml-1 rounded bg-transparent px-1 py-0.5 text-sm font-semibold text-ink focus:outline-none"
              >
                <option value="math">Math</option>
                <option value="science">Science</option>
              </select>
              <div className="font-mono text-xs text-ink/50">Grade 6</div>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-sage/40 px-3 py-1 font-mono text-xs tracking-wide text-sage uppercase">
            <span className="h-1.5 w-1.5 rounded-full bg-sage" />
            {phaseLabel}
          </div>
        </div>

        <div className="flex flex-col gap-5 px-6 py-7">
          {messages.length === 0 && (
            <p className="text-sm text-ink/50">Ask a question below to start a session.</p>
          )}
          {messages.map((message, i) => (
            <div key={i} className={`flex ${message.role === "student" ? "justify-end" : ""}`}>
              <div
                className={
                  message.role === "student"
                    ? "max-w-[82%] rounded-tl-lg rounded-tr-sm rounded-bl-lg rounded-br-lg bg-paper-3 px-4 py-3 text-sm text-ink"
                    : "max-w-full whitespace-pre-wrap text-sm leading-relaxed text-ink/90"
                }
              >
                {message.content}
              </div>
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="border-t border-rule px-6 py-5">
          <textarea
            placeholder={attaching ? "Reading your file..." : "Ask a question, or answer the one above..."}
            required
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={attaching}
            className="w-full rounded border border-rule bg-paper px-3 py-2 text-sm text-ink placeholder:text-ink/40 focus:outline-none focus:ring-1 focus:ring-gold disabled:opacity-50"
          />
          <p className="mt-2 text-xs text-ink/45">
            Attached a photo, PDF, or Word file? Check the transcribed text above is correct before
            sending, fix anything it misread.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <input
              type="file"
              accept={ACCEPTED_UPLOAD_TYPES}
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={attaching || loading}
              className="rounded border border-rule px-3 py-2 text-sm text-ink hover:bg-paper-3 disabled:opacity-50"
            >
              {attaching ? "Reading..." : "Attach file"}
            </button>
            <button
              type="submit"
              disabled={loading || attaching}
              className="rounded bg-ink px-4 py-2 text-sm font-medium text-paper transition hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Thinking..." : "Ask"}
            </button>
          </div>
          {attachError && <p className="mt-2 text-sm text-red-600">{attachError}</p>}
        </form>
      </div>
    </main>
  );
}
