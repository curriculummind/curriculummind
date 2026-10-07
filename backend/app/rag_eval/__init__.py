"""
RAGAS-style offline evaluation metrics (Decision 032): faithfulness,
answer relevancy, context precision, and context recall, scored against
a curated golden set by `scripts/run_evaluation.py`. Reimplements each
metric's definition using this codebase's own LLMClient/EmbeddingClient
abstractions rather than depending on the `ragas` package, which is
built around LangChain chat models this stack doesn't use -- the same
"same job, different mechanism" substitution Decision 016 already made
for cross-encoder reranking.

Named distinctly from the existing `app/evaluation/` package, which is
an unrelated, already-shipped live feature (per-message faithfulness/
relevance scoring for the guardian dashboard and progress tracking,
Decision 023) -- this is an offline harness over a hand-curated golden
set, not something that runs against real student traffic.
"""
