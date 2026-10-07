"""
RAGAS-style offline evaluation harness (Decision 032).

Runs the golden set (`scripts/evaluation/golden_set.py`) through the
real, unmocked retrieval + generation pipeline -- the same `retrieve()`
and `generate_grounded_response()` the live app calls, not a stand-in --
and scores each answerable case on four metrics (`app/rag_eval/`):
context precision, context recall, faithfulness, answer relevancy. The
four deliberately out-of-corpus cases are scored instead on whether the
existing low-confidence fallback correctly triggered, since there's no
retrieved evidence to run the four RAGAS scores against.

Judges every metric with the full model (`anthropic_model`), not the
fast classifier model the live app uses for its four classification
calls (Decision 030): this harness runs offline with no user waiting,
so the latency/cost tradeoff that justified the smaller model in
production doesn't apply, and a judge should be tuned for reliability
the same way correctness classification was (Decision 031).

Writes `docs/evaluation-report.md` (human-readable, committed) and
`scripts/evaluation/results.json` (raw per-case scores, for diffing
after future prompt/retrieval changes).

Costs real Anthropic + OpenAI API usage and takes a few minutes to run
for the full golden set -- not a free or instant operation.

Run with: python -m scripts.run_evaluation
"""

import asyncio
import json
import os
import statistics
import sys
from datetime import UTC, datetime

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.db import get_pool
from app.providers.embeddings import OpenAIEmbeddingClient
from app.providers.llm import AnthropicLLMClient
from app.rag_eval.answer_relevancy import score_answer_relevancy
from app.rag_eval.context_precision import judge_relevance
from app.rag_eval.context_recall import score_context_recall
from app.rag_eval.faithfulness import score_faithfulness
from app.rag_eval.models import CaseResult
from app.retrieval.pipeline import retrieve
from app.tutoring.generation import generate_grounded_response
from scripts.evaluation.golden_set import GOLDEN_SET, GoldenCase

load_dotenv()

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "evaluation", "results.json")
REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "evaluation-report.md")

METRIC_FIELDS = ("context_precision", "context_recall", "faithfulness", "answer_relevancy")


async def _generate_answer(case: GoldenCase, evidence, llm) -> str:
    chunks = [
        token
        async for token in generate_grounded_response(
            case.question,
            evidence,
            history=[],
            subject=case.subject_slug,
            grade_band=case.grade_band,
            llm=llm,
            is_assignment=False,
            strategy="guiding",
        )
    ]
    return "".join(chunks)


async def _run_case(case: GoldenCase, *, pool, embedder, llm) -> CaseResult:
    result = await retrieve(
        case.question,
        subject_slug=case.subject_slug,
        grade_band=case.grade_band,
        embedder=embedder,
        pool=pool,
        concept_slug=case.concept_slug,
    )

    # The live pipeline's actual confidence band isn't retrieve()'s raw
    # similarity gate alone -- _relevance_check_node (Decision 016)
    # re-judges every candidate with the LLM and can flip a similarity
    # "high" to "low" when nothing retrieved is genuinely relevant, or
    # the reverse. Reusing the same judgments for the precision score
    # below avoids asking the LLM about the same chunks twice.
    relevance_judgments = await judge_relevance(case.question, result.evidence, llm)
    band = "high" if any(relevance_judgments) else "low"
    precision = sum(relevance_judgments) / len(relevance_judgments) if relevance_judgments else 0.0

    if case.expect_fallback:
        return CaseResult(
            case_id=case.id,
            question=case.question,
            band=band,
            evidence_count=len(result.evidence),
            expect_fallback=True,
            fallback_correct=(band == "low"),
            notes="out-of-corpus probe" if band == "low" else "expected low confidence, got high",
        )

    if band == "low":
        return CaseResult(
            case_id=case.id,
            question=case.question,
            band=band,
            evidence_count=len(result.evidence),
            notes="retrieval/relevance missed -- no evidence to score the four RAGAS metrics against",
        )

    answer = await _generate_answer(case, result.evidence, llm)
    recall, faithfulness, relevancy = await asyncio.gather(
        score_context_recall(case.reference_facts, result.evidence, llm),
        score_faithfulness(answer, result.evidence, llm),
        score_answer_relevancy(case.question, answer, llm, embedder),
    )
    return CaseResult(
        case_id=case.id,
        question=case.question,
        band=band,
        evidence_count=len(result.evidence),
        answer=answer,
        context_precision=precision,
        context_recall=recall,
        faithfulness=faithfulness,
        answer_relevancy=relevancy,
    )


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "--"


def _write_report(results: list[CaseResult]) -> None:
    scored = [r for r in results if not r.expect_fallback]
    fallback = [r for r in results if r.expect_fallback]
    retrieval_misses = [r for r in scored if r.answer is None]
    answered = [r for r in scored if r.answer is not None]

    aggregates = {field: _mean([getattr(r, field) for r in answered]) for field in METRIC_FIELDS}
    fallback_accuracy = _mean([1.0 if r.fallback_correct else 0.0 for r in fallback])

    lines = [
        "# CurriculumMind evaluation report",
        "",
        (
            f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by "
            "`scripts/run_evaluation.py` (Decision 032), against the real retrieval + generation "
            "pipeline and a live Supabase-backed corpus -- not a mocked run."
        ),
        "",
        "## Methodology",
        "",
        (
            "Four RAGAS-style metrics, scored by an LLM judge on the full generation model "
            "(not the faster classifier model the live app uses for speed -- this harness runs "
            "offline, so reliability was prioritized over latency):"
        ),
        "",
        (
            "- **Context precision** -- of the chunks retrieval returned, what fraction are "
            "actually usable to answer the question (reuses the same relevance judgment the "
            "live pipeline itself applies, Decision 016)."
        ),
        (
            "- **Context recall** -- of the key facts a complete answer needs, what fraction "
            "does the retrieved evidence collectively contain."
        ),
        (
            "- **Faithfulness** -- of the claims the generated answer makes, what fraction are "
            "actually supported by the retrieved evidence, rather than the model's general knowledge."
        ),
        (
            "- **Answer relevancy** -- does the answer address the question that was actually "
            "asked (RAGAS's own method: reverse-engineer questions from the answer, embed, and "
            "compare to the original question)."
        ),
        "",
        (
            f"{len(scored)} cases expect a direct, groundable answer; {len(fallback)} are "
            "deliberately out-of-corpus probes that instead check whether the existing "
            "low-confidence fallback correctly declines to answer, since there's no evidence to "
            "run the four scores above against."
        ),
        "",
        (
            "**Scope limitation, named plainly:** every case here is single-turn, with no prior "
            "conversation history, scored in the default \"guiding\" strategy. Multi-turn "
            "guided-discovery follow-ups and the escalated strategies (explain, confirm_*) don't "
            "produce one single \"the answer\" to hold up against these criteria, so they aren't "
            "covered by this harness yet."
        ),
        "",
        "## Aggregate scores",
        "",
        "| Metric | Mean | Cases scored |",
        "| --- | --- | --- |",
    ]
    for field in METRIC_FIELDS:
        label = field.replace("_", " ")
        value = aggregates[field]
        lines.append(f"| {label} | {f'{value:.2f}' if value is not None else 'n/a'} | {len(answered)} |")
    lines.append(
        f"| fallback correctly triggered | {f'{fallback_accuracy:.2f}' if fallback_accuracy is not None else 'n/a'} "
        f"| {len(fallback)} |"
    )
    if retrieval_misses:
        lines.append("")
        lines.append(
            f"**{len(retrieval_misses)} of {len(scored)} answerable cases had retrieval miss entirely** "
            "(low confidence where a direct answer was expected) -- these are excluded from the "
            "aggregates above and listed in the per-case breakdown with no scores, not silently dropped."
        )

    lines += [
        "",
        "## Per-case results",
        "",
        "| Case | Band | Precision | Recall | Faithfulness | Relevancy | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in scored:
        lines.append(
            f"| {r.case_id} | {r.band} | {_fmt(r.context_precision)} | {_fmt(r.context_recall)} | "
            f"{_fmt(r.faithfulness)} | {_fmt(r.answer_relevancy)} | {r.notes} |"
        )

    lines += [
        "",
        "## Fallback probes",
        "",
        "| Case | Band | Correctly declined | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for r in fallback:
        lines.append(f"| {r.case_id} | {r.band} | {'yes' if r.fallback_correct else 'no'} | {r.notes} |")

    lines.append("")
    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


async def main() -> None:
    settings = get_settings()
    pool = get_pool()
    await pool.open()
    embedder = OpenAIEmbeddingClient(api_key=settings.openai_api_key, model=settings.openai_embedding_model)
    llm = AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model)

    try:
        results = []
        for case in GOLDEN_SET:
            print(f"Running {case.id}...")
            result = await _run_case(case, pool=pool, embedder=embedder, llm=llm)
            results.append(result)
            print(f"  band={result.band} notes={result.notes!r}")
    finally:
        await pool.close()

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump([r.model_dump() for r in results], f, indent=2)

    _write_report(results)
    print(f"\nWrote {RESULTS_PATH} and {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
