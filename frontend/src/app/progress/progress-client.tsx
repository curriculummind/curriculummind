"use client";

import { Logo } from "@/components/logo";
import { TopicChart } from "@/components/topic-chart";

/** Combined cross-subject mastery overview -- Math and Science side by side, read-only (no chat here). */
export function ProgressClient() {
  return (
    <main className="mx-auto flex min-h-full max-w-5xl flex-col px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <Logo />
        <a href="/home" className="text-sm text-ink/55 hover:text-ink">
          &larr; Back to home
        </a>
      </div>

      <h1 className="mb-1 font-display text-2xl font-medium text-ink">Your progress</h1>
      <p className="mb-8 text-sm text-ink/60">Every topic across both subjects, plotted against your mastery tier.</p>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="flex flex-col overflow-hidden rounded-lg border border-rule bg-paper-3">
          <div className="border-b border-rule px-5 py-4">
            <h2 className="font-display text-lg font-medium text-ink">Math</h2>
          </div>
          <TopicChart subject="math" />
        </div>
        <div className="flex flex-col overflow-hidden rounded-lg border border-rule bg-paper-3">
          <div className="border-b border-rule px-5 py-4">
            <h2 className="font-display text-lg font-medium text-ink">Science</h2>
          </div>
          <TopicChart subject="science" />
        </div>
      </div>
    </main>
  );
}
