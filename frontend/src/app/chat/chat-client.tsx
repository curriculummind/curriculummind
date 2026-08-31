"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { SelectedTopic, TopicChart } from "@/components/topic-chart";

type ChatMessage = {
  role: "student" | "assistant";
  content: string;
  strategy?: string;
  citationCode?: string;
  citationFramework?: string;
};

const ACCEPTED_UPLOAD_TYPES =
  "image/jpeg,image/png,image/webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

/**
 * The guided-discovery prompt (Decision 015) always separates a stated
 * anchor from a genuine follow-up question with a blank line -- this
 * splits on that convention so the question can be styled distinctly,
 * without needing the backend to return structured output.
 */
function splitAnchorAndPrompt(content: string): { anchor: string; prompt: string | null } {
  const parts = content.split(/\n\s*\n/);
  const last = parts[parts.length - 1]?.trim();
  if (parts.length > 1 && last?.endsWith("?")) {
    return { anchor: parts.slice(0, -1).join("\n\n").trim(), prompt: last };
  }
  return { anchor: content, prompt: null };
}

function shortFrameworkName(name: string): string {
  return name.split(" State Standards")[0];
}

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
  const [selectedTopic, setSelectedTopic] = useState<SelectedTopic | null>(null);
  const [progressVersion, setProgressVersion] = useState(0);
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

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "",
        strategy: res.headers.get("X-Tutoring-Strategy") ?? undefined,
        citationCode: res.headers.get("X-Citation-Code") ?? undefined,
        citationFramework: res.headers.get("X-Citation-Framework") ?? undefined,
      },
    ]);

    const reader = res.body?.getReader();
    const decoder = new TextDecoder();

    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: next[next.length - 1].content + chunk,
        };
        return next;
      });
    }

    setLoading(false);
    setProgressVersion((v) => v + 1);
  }

  function handleSubjectChange(next: string) {
    setSubject(next);
    setMessages([]);
    setConversationId(null);
    setTutoringPhase("guiding");
    setSelectedTopic(null);
  }

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  const subjectLabel = subject === "math" ? "Math" : "Science";
  const phaseLabel = tutoringPhase === "confirming" ? "Confirming" : "Guiding";

  return (
    <div className="grid h-screen grid-cols-[3fr_7fr]">
      <TopicChart
        subject={subject}
        onSubjectChange={handleSubjectChange}
        selected={selectedTopic}
        onSelectTopic={setSelectedTopic}
        version={progressVersion}
      />

      <main className="flex h-screen min-h-0 flex-col">
        <div className="flex items-center justify-between border-b border-rule px-8 py-[18px]">
          <div className="flex items-center gap-3.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-gold to-[color-mix(in_srgb,var(--gold),black_35%)] font-display text-sm font-semibold text-paper">
              {subjectLabel[0]}
            </div>
            <div>
              <h1 className="font-display text-[1.05rem] font-semibold text-ink">
                {selectedTopic ? selectedTopic.topicName : `${subjectLabel} session`}
              </h1>
              <div className="font-mono text-xs text-ink/50">
                {selectedTopic ? `${selectedTopic.moduleName} · Grade 6` : "Grade 6"}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-2 rounded-full border border-sage/40 px-3 py-1 font-mono text-xs tracking-wide text-sage uppercase">
              <span className="h-1.5 w-1.5 rounded-full bg-sage" />
              {phaseLabel}
            </div>
            <button
              onClick={handleLogout}
              className="text-sm text-ink/55 underline underline-offset-2 hover:text-ink"
            >
              Log out
            </button>
          </div>
        </div>

        <div className="flex min-h-0 flex-1 justify-center overflow-y-auto px-8 py-7">
          <div className="flex w-full max-w-[700px] flex-col gap-5">
            {messages.length === 0 && (
              <p className="text-sm text-ink/50">Ask a question below to start a session.</p>
            )}
            {messages.map((message, i) => {
            if (message.role === "student") {
              return (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[82%] rounded-tl-lg rounded-tr-sm rounded-bl-lg rounded-br-lg bg-paper-3 px-4 py-3 text-sm text-ink">
                    {message.content}
                  </div>
                </div>
              );
            }

            if (message.strategy === "confirm_wrapup") {
              return (
                <div
                  key={i}
                  className="flex items-start gap-3 rounded-md border border-sage/30 bg-sage/8 px-4 py-3.5 text-sm leading-relaxed text-ink/85"
                >
                  <div>
                    <strong className="mb-1.5 block font-mono text-[0.68rem] tracking-[0.08em] text-sage uppercase">
                      Confirmed &middot; Wrap-up
                    </strong>
                    {message.content}
                  </div>
                </div>
              );
            }

            const { anchor, prompt } = splitAnchorAndPrompt(message.content);
            return (
              <div key={i} className="max-w-full text-sm leading-relaxed text-ink/90">
                {message.citationCode && (
                  <span className="mb-2.5 inline-flex items-center gap-1.5 rounded-sm border border-rule px-2 py-1 font-mono text-[0.66rem] text-ink/55">
                    {message.citationFramework ? shortFrameworkName(message.citationFramework) : "Standard"}
                    &middot; {message.citationCode}
                  </span>
                )}
                <p className="whitespace-pre-wrap">{anchor}</p>
                {prompt && (
                  <p className="mt-2.5 border-l-2 border-gold pl-3.5 font-display text-base text-gold italic">
                    {prompt}
                  </p>
                )}
              </div>
            );
            })}
          </div>
        </div>

        <div className="flex justify-center border-t border-rule px-8 py-4">
          <form onSubmit={handleSubmit} className="w-full max-w-[700px]">
            <textarea
              placeholder={attaching ? "Reading your file..." : "Ask a question, or answer the one above..."}
              required
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
              disabled={attaching}
              className="w-full rounded border border-rule bg-paper-2 px-3 py-2 text-sm text-ink placeholder:text-ink/40 focus:outline-none focus:ring-1 focus:ring-gold disabled:opacity-50"
            />
            <p className="mt-2 text-xs text-ink/45">
              Attached a photo, PDF, or Word file? Check the transcribed text above is correct before
              sending, fix anything it misread.
            </p>
            <div className="mt-3 flex items-center justify-between gap-2">
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
                aria-label={loading ? "Thinking" : "Ask"}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-ink text-paper transition hover:opacity-90 disabled:opacity-50"
              >
                {loading ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 19V5M5 12l7-7 7 7" />
                  </svg>
                )}
              </button>
            </div>
            {attachError && <p className="mt-2 text-sm text-red-600">{attachError}</p>}
          </form>
        </div>
      </main>
    </div>
  );
}
