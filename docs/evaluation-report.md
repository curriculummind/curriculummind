# CurriculumMind evaluation report

Generated 2026-10-07 00:08 UTC by `scripts/run_evaluation.py` (Decision 032), against the real retrieval + generation pipeline and a live Supabase-backed corpus -- not a mocked run.

## Methodology

Four RAGAS-style metrics, scored by an LLM judge on the full generation model (not the faster classifier model the live app uses for speed -- this harness runs offline, so reliability was prioritized over latency):

- **Context precision** -- of the chunks retrieval returned, what fraction are actually usable to answer the question (reuses the same relevance judgment the live pipeline itself applies, Decision 016).
- **Context recall** -- of the key facts a complete answer needs, what fraction does the retrieved evidence collectively contain.
- **Faithfulness** -- of the claims the generated answer makes, what fraction are actually supported by the retrieved evidence, rather than the model's general knowledge.
- **Answer relevancy** -- does the answer address the question that was actually asked (RAGAS's own method: reverse-engineer questions from the answer, embed, and compare to the original question).

18 cases expect a direct, groundable answer; 4 are deliberately out-of-corpus probes that instead check whether the existing low-confidence fallback correctly declines to answer, since there's no evidence to run the four scores above against.

**Scope limitation, named plainly:** every case here is single-turn, with no prior conversation history, scored in the default "guiding" strategy. Multi-turn guided-discovery follow-ups and the escalated strategies (explain, confirm_*) don't produce one single "the answer" to hold up against these criteria, so they aren't covered by this harness yet.

## Aggregate scores

| Metric | Mean | Cases scored |
| --- | --- | --- |
| context precision | 0.49 | 17 |
| context recall | 0.94 | 17 |
| faithfulness | 0.99 | 17 |
| answer relevancy | 0.71 | 17 |
| fallback correctly triggered | 1.00 | 4 |

**1 of 18 answerable cases had retrieval miss entirely** (low confidence where a direct answer was expected) -- these are excluded from the aggregates above and listed in the per-case breakdown with no scores, not silently dropped.

## Per-case results

| Case | Band | Precision | Recall | Faithfulness | Relevancy | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| ratios-unit-rate | high | 0.80 | 1.00 | 1.00 | 0.71 |  |
| fractions-dividing | high | 0.87 | 0.33 | 1.00 | 0.58 |  |
| expressions-variable | high | 0.60 | 1.00 | 1.00 | 0.70 |  |
| rational-absolute-value | high | 0.53 | 1.00 | 1.00 | 0.74 |  |
| surface-area-prism | high | 0.67 | 1.00 | 1.00 | 0.64 |  |
| statistics-mad | high | 0.87 | 0.67 | 1.00 | 0.71 |  |
| cell-organelles | high | 0.62 | 1.00 | 1.00 | 0.71 |  |
| genetics-dna-allele | high | 0.27 | 1.00 | 1.00 | 0.81 |  |
| evolution-natural-selection | high | 0.60 | 1.00 | 0.86 | 0.65 |  |
| ecosystems-producer | high | 0.70 | 1.00 | 1.00 | 0.80 |  |
| human-body-nervous-circulatory | high | 0.07 | 1.00 | 1.00 | 0.78 |  |
| plant-photosynthesis | high | 0.07 | 1.00 | 1.00 | 0.63 |  |
| protists-fungi | high | 0.13 | 1.00 | 1.00 | 0.90 |  |
| virus-vs-bacteria | low | -- | -- | -- | -- | retrieval/relevance missed -- no evidence to score the four RAGAS metrics against |
| vertebrate-backbone | high | 0.53 | 1.00 | 1.00 | 0.78 |  |
| invertebrate-no-backbone | high | 0.53 | 1.00 | 1.00 | 0.71 |  |
| behavior-instinct-vs-learned | high | 0.11 | 1.00 | 1.00 | 0.79 |  |
| hypothesis-scientific-method | high | 0.40 | 1.00 | 1.00 | 0.48 |  |

## Fallback probes

| Case | Band | Correctly declined | Notes |
| --- | --- | --- | --- |
| fallback-pythagorean | low | yes | out-of-corpus probe |
| fallback-slope | low | yes | out-of-corpus probe |
| fallback-moon-phases | low | yes | out-of-corpus probe |
| fallback-chemical-energy | low | yes | out-of-corpus probe |

