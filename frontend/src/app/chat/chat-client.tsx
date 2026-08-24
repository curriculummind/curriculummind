"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

type ChatMessage = {
  role: "student" | "assistant";
  content: string;
};

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
  const [loading, setLoading] = useState(false);

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
  }

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">CurriculumMind — Grade 6</h1>
        <button onClick={handleLogout} className="text-sm text-gray-500 underline">
          Log out
        </button>
      </div>

      <select
        value={subject}
        onChange={(e) => handleSubjectChange(e.target.value)}
        className="mt-6 rounded border px-3 py-2"
      >
        <option value="math">Math</option>
        <option value="science">Science</option>
      </select>

      <div className="mt-4 flex flex-col gap-3">
        {messages.map((message, i) => (
          <div
            key={i}
            className={
              message.role === "student"
                ? "self-end rounded bg-black px-4 py-2 text-white"
                : "self-start whitespace-pre-wrap rounded border bg-gray-50 px-4 py-2 text-sm"
            }
          >
            {message.content}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <textarea
          placeholder="Ask a question, or answer the one above..."
          required
          rows={2}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="rounded border px-3 py-2"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-black px-3 py-2 text-white disabled:opacity-50"
        >
          {loading ? "Thinking..." : "Ask"}
        </button>
      </form>
    </main>
  );
}
