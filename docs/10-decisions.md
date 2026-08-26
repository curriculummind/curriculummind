# CurriculumMind Engineering Decisions

This document records important product and engineering decisions made during the project.

Each decision should include:

* Decision
* Date (optional)
* Reason
* Impact

---

# Decision 001

## Decision

The MVP will target **Grades 6–12 only**.

## Reason

Reducing the scope allows the team to focus on building a polished, production-quality tutoring platform rather than attempting to support every K–12 grade level.

The architecture will remain flexible enough to support K–5 later.

## Impact

* Smaller curriculum corpus
* Simpler pedagogical policies
* Faster development
* Easier testing
* Better capstone scope

---

# Decision 002

## Decision

The MVP subjects will be:

* Computer Science
* Science

## Reason

Computer Science showcases AI tutoring particularly well through debugging, code explanation, progressive hints, and assignment detection.

Science complements this with conceptual learning and curriculum-grounded explanations.

Additional subjects can be added later.

---

# Decision 003

## Decision

CurriculumMind will use Retrieval-Augmented Generation (RAG) rather than training or fine-tuning a foundation model.

## Reason

The project's contribution is the tutoring architecture, curriculum grounding, agentic reasoning, and pedagogical workflow—not building a new language model.

---

# Decision 004

## Decision

Claude Code will be the primary AI coding agent.

## Reason

Claude Code is particularly strong at:

* architecture
* large codebases
* multi-file refactoring
* long engineering specifications
* maintaining consistency across the project

---

# Decision 005

## Decision

Git will serve as the project's source of truth.

## Reason

Project knowledge should live in version-controlled documentation rather than relying on AI conversation history.

All major architectural and product decisions should be documented here.

---

# Decision 006

**Date:** 2026-08-21 (adopted 2026-08-26)

## Decision

The tutoring engine's decision phase runs as a deterministic LangGraph `StateGraph` (`app/tutoring/graph.py`) — five typed nodes (`retrieve`, `detect_assignment`, `relevance_check`, `classify_correctness`, `select_strategy`) with two conditional branches (low-confidence relevance fallback, band-gated correctness classification) — rather than an autonomous agent that decides at runtime which tools to call. Generation (streaming tokens to the client) deliberately stays outside the graph, in the router, since a single `ainvoke` call returning one final state doesn't fit a token-streaming response.

## Reason

Letting a language model decide whether to run a curriculum lookup makes core pedagogical guarantees probabilistic instead of guaranteed. A tutoring product needs every response to be auditable: which retrieval ran, and why a given strategy was chosen, for any message. Between this decision's original date and its adoption, the pipeline grew real branching logic worth modeling explicitly: the Decision 016 relevance fallback, Decision 017 assignment detection, and Decision 019 struggle-escalation strategy selection had all been implemented as a hand-written `asyncio.gather`/if-else chain in the router -- functionally correct, but exactly the kind of ad hoc branching this decision originally said LangGraph should replace. The `retrieve` and `detect_assignment` nodes both have edges from `__start__` with no dependency between them, so LangGraph schedules them concurrently -- the same behavior the old `asyncio.gather` call provided, now expressed as graph structure instead of a manual concurrency primitive.

## Impact

* Every node wraps an existing, already-tested module (`retrieval/pipeline.py`, `assignment.py`, `relevance.py`, `correctness.py`, `escalation.py`) completely unchanged -- this changed orchestration, not behavior. Verified by comparing decision output directly against three representative cases (on-topic, off-topic, assignment-like) and by re-running the full escalation and assignment-detection scenarios through the live `/tutor/ask` endpoint post-refactor -- identical behavior to before the graph existed.
* The compiled graph exposes `.get_graph().draw_mermaid()`, producing a real diagram of the pipeline as actually executed -- useful both for capstone demonstration and as a starting point for the observability gap named in Principle 11 (a future trace endpoint could stream `.astream()` node-by-node instead of only the final state).
* A safety-check node was not added -- safety screening is still unbuilt (M1 work per the router's own docstring). The graph structure makes adding it later a matter of one more node plus edges, not a redesign, which is the extension-without-redesign guarantee this decision was meant to buy.
* The four "tools" described in the original capstone proposal (`curriculum_lookup`, `student_history`, `assignment_detector`, `parent_alert`) remain deterministic pipeline stages backed by plain service code, not LLM-invoked functions -- unchanged from the original decision.

---

# Decision 007

**Date:** 2026-08-21

## Decision

`parent_alert` is not a tool the tutoring agent can invoke mid-conversation. It becomes an asynchronous job, triggered by a threshold check over aggregated student learning signals, running in the background worker after a conversation turn completes.

## Reason

An escalation to a parent or guardian is a sensitive action. It should fire from a deterministic threshold on accumulated evidence (repeated confusion, repeated assignment-support patterns), not from a language model's in-the-moment judgment call during a chat turn.

## Impact

* Removes a latency-sensitive, safety-sensitive decision from the synchronous request path entirely.
* Alerts are generated by the `evaluation/` module, not the `tutoring/` module.

---

# Decision 008

**Date:** 2026-08-21

## Decision

Curriculum is modeled as a curriculum-agnostic Concept taxonomy. CurriculumFramework and Standard are a separate, lighter mapping layer that attaches to Concepts many-to-many, rather than a single flat "Curriculum" entity that content and standards both hang off directly.

## Reason

Common Core, NGSS, CBSE, and school-specific syllabi do not share a common shape. Forcing them into one schema would either distort future curricula or require rework when a second framework is added. Keeping Concept as the stable unit means the tutoring engine, retrieval filters, and strategy selection never change shape when a new curriculum is introduced.

## Impact

* One additional join table (Standard-to-Concept mapping) versus a flatter model.
* Adding a new curriculum framework (e.g. CBSE) later is a data/ingestion task — a new framework row, standard mappings, and tagged content — not a schema or engine change.
* The MVP builds this split now, populated with a single framework (US, Common Core/NGSS-aligned).

---

# Decision 009

**Date:** 2026-08-21

## Decision

Guardians read student progress through a derived summary table that the background worker materializes, not through Row Level Security policies granting filtered access to raw Conversation or Message rows.

## Reason

RLS can restrict *which rows* a guardian sees, but it cannot cleanly express "summary only, never the transcript." Structuring guardian access so there is no query path to raw conversation data for that role — rather than a correctly-written filter — makes the privacy boundary structural instead of policy-dependent.

## Impact

* Requires an async materialization job (already needed for evaluation signals) to also populate guardian-facing summaries.
* Guardians hold no RLS grant on Conversation or Message tables at all.

---

# Decision 010

**Date:** 2026-08-21

## Decision

All tutoring-domain reads and writes (conversations, messages, progress, guardian summaries, curriculum metadata) go through the FastAPI backend. The Next.js frontend calls Supabase directly only for authentication session handling.

## Reason

Almost nothing in this domain is simple CRUD once privacy and pedagogical rules apply. Keeping business rules in one backend, rather than split between RLS policies and application code, matches the "backend defines the product" principle and avoids a second, harder-to-audit place where access rules could diverge.

## Impact

* More backend endpoints to build than a Supabase-direct-from-frontend pattern would require.
* A single, testable boundary for every rule that matters (e.g. guardian summary-only access from Decision 009).

---

# Decision 011

**Date:** 2026-08-21

## Decision

The backend is a modular monolith: one FastAPI service with strong internal module boundaries (`tutoring/`, `retrieval/`, `curriculum/`, `identity/`, `evaluation/`, `observability/`), sharing a codebase with a background worker process. The frontend is a separate Next.js application. No microservices at this stage.

## Reason

Microservices solve a multi-team, independent-deployment problem this project does not yet have, and the tutoring pipeline's modules are genuinely coupled around one domain model and one latency-sensitive request path — splitting them into services would add network calls to the pipeline with the tightest latency budget in the system, for no scaling benefit at MVP traffic.

## Impact

* Two deployable units total: frontend and backend.
* Module boundaries are drawn so `retrieval/` — the most compute-heavy path — could be extracted into its own service later without redesigning the domain model, if traffic ever justifies it.

---

# Decision 012

**Date:** 2026-08-21

## Decision

CurriculumMind will be deployed to production at **curriculummind.com**, with the frontend on Vercel, the backend (API service + background worker) on Render, Supabase for authentication and PostgreSQL/pgvector, and Sentry for error tracking on both frontend and backend.

## Reason

CurriculumMind is intended to become a real commercial product, not only a capstone deliverable. This deployment stack is the simplest reliable option that supports a custom production domain, HTTPS, environment separation, and managed operations without introducing infrastructure (Kubernetes, self-managed services) the project has no current need for.

## Impact

* DNS: apex/`www` route to Vercel; an `api` subdomain routes to Render.
* CORS on the backend is restricted to the production domain plus local development origins.
* Separate Supabase projects (or schemas) and separate environment variable sets are used for development/staging versus production.

---

# Decision 013

**Date:** 2026-08-21

## Decision

The initial build and content-ingestion target narrows to **Grade 6, Mathematics and Science**, sourced from free, open-license content — EngageNY/Eureka Math (Grade 6) for math, CK-12 for science — rather than starting ingestion across the full Grades 6–12, Computer Science + Science scope from Decisions 001–002.

## Reason

EngageNY and CK-12 are the cleanest available sources actually built for this grade band, are free to use for non-commercial/educational purposes, and let the full tutoring pipeline (retrieval, assignment detection, strategy selection, evaluation) be validated against real content quickly. Both sources' licenses (CC BY-NC-SA and a CK-12 "Educational Purposes" license, respectively) explicitly exclude commercial use — acceptable for the capstone, not for a monetized product.

## Impact

* Decisions 001 and 002 remain the target MVP scope the architecture is built for. This decision narrows the *initial content and build target* to a subset of that scope, not a replacement for it — Grades 7–12 and Computer Science remain the next expansion step once this slice works, added via configuration and content ingestion (see the architecture proposal, §14 Subject Architecture and §29 Future Extension Model), with no tutoring-engine change required.
* **Before any commercial launch on curriculummind.com, the content corpus must be replaced or re-licensed.** Options: secure explicit written commercial permission from CK-12 and/or Great Minds/NYSED (EngageNY); verify and use only the specific OpenStax titles licensed CC BY (not CC BY-NC-SA) where grade-appropriate; source public-domain/government material; or commission original content. This is a tracked pre-launch requirement.
* Common Core (math) and NGSS (science) standards documents are sourced separately as the Standard/CurriculumFramework mapping layer (§13 of the architecture proposal), not as retrievable teaching content. Their licensing is generally more permissive than CK-12/EngageNY's content licenses but should still be confirmed before commercial use.

---

# Decision 015

**Date:** 2026-08-24

## Decision

Guided-discovery (Socratic-style) tutoring is the default response mode across **all grades 6-12**, not grade-gated as originally proposed in the architecture (§10, which had defaulted direct explanation for grades 6-9 and Socratic for grades 10-12 only). Each turn stays short: a minimal concrete anchor or example, then a genuine question the student must answer before getting more -- not a full paragraph explanation with a token question appended, and not a bare question with zero grounding. Full direct explanation remains available as an escalation path (explicit student request, or repeated non-progress after a couple of guided turns), not as the default.

## Reason

The M0 generation prompt (direct explanation only, since strategy selection wasn't built yet) produced a paragraph lecture indistinguishable from asking a general-purpose chatbot the same question. That directly undercuts the product's core thesis -- "a tutor should help students think rather than replace thinking" -- and its differentiation from Claude/GPT used directly. Pure lecture answers fail that test regardless of grade band.

## Impact

* Reshapes the default strategy in the M1 pedagogical policy system (§10) before that system is built -- no rework of shipped M0 code, since strategy selection didn't exist yet.
* The "direct explanation default for 6-9" line in architecture §10 is superseded by this decision for the default case; direct explanation remains a real strategy, just not the default one.
* Prompt design for the default strategy needs to produce short, anchored, question-ending turns -- not full explanations -- which is a real prompt-engineering task, not just a strategy-selection routing change.

---

# Decision 014

**Date:** 2026-08-21

## Decision

The runtime LLM provider (classification and generation) is **Anthropic Claude**. The embedding provider (RAG ingestion and query embedding) is **OpenAI's `text-embedding-3` family**. Both sit behind the `LLMClient` / `EmbeddingClient` interfaces from the architecture proposal (§17), each with exactly one concrete adapter for now.

## Reason

Claude gives strong instruction-following and structured-output reliability for the classification and generation nodes, and keeps the runtime provider consistent with the team's existing tooling. Anthropic does not offer an embeddings API, so embeddings necessarily come from a second provider; OpenAI's `text-embedding-3` models are inexpensive, well-documented, and pair cleanly with pgvector regardless of which provider handles generation.

## Impact

* Two provider API keys are required in the backend environment: an Anthropic key and an OpenAI key.
* Swapping either provider later is a new adapter class behind the existing interface plus a config flag — see §17 and §33 of the architecture proposal. Swapping the embedding provider specifically also requires re-embedding the corpus (a backfill job, not a schema change).

---

# Decision 016

**Date:** 2026-08-24

## Decision

Retrieval confidence is no longer decided by a raw cosine-similarity threshold alone. When similarity-based confidence is "low," the pipeline now asks the model directly whether the top retrieved chunk can actually answer the student's question before falling back to "no curriculum material on this."

## Reason

Real testing showed the similarity distributions for on-topic and off-topic questions overlap on a corpus this size: "what is a ribosome" (genuinely covered by ingested content) scored 0.23 cosine similarity, while "how do I bake a cake" (genuinely off-topic) scored 0.32 -- higher -- because the Ratios and Unit Rates content uses recipe/baking examples. No single threshold value can cleanly separate cases like that; moving the number only trades one failure mode for another, which is exactly what happened across the last two threshold recalibrations (Decision 016 supersedes the threshold-only approach documented in `app/retrieval/confidence.py`'s calibration comment). This is the evidence-driven trigger the architecture proposal's own decision table (§31) called for before adding a reranking-style step -- not a routine adjustment.

## Impact

* One additional classification call (`generate_structured`, built earlier but previously unused) runs only on the low-confidence path, not on every request -- latency and cost impact is bounded to ambiguous cases.
* `app/retrieval/confidence.py`'s pure-similarity gate is unchanged and still runs first; this is a second-pass escalation, not a replacement.
* A full dedicated reranker (cross-encoder or similar) remains deferred -- this targeted fix resolved the demonstrated failure cases without that heavier addition.

---

# Decision 017

**Date:** 2026-08-25

## Decision

Assignment detection is implemented as a single structured LLM classification (`app/tutoring/assignment.py`, `detect_assignment`) run in parallel with retrieval on every request, whose boolean result strengthens the existing guided-discovery generation prompt (`app/tutoring/generation.py`) rather than triggering a separate routing branch, strategy, or blocking gate.

## Reason

The product principle this addresses (`docs/00-project-memory.md`: "detect assignment-like requests") is about preventing the tutor from handing a student the final answer to graded work, not about refusing to engage with assignment-derived questions -- guided discovery already withholds direct answers by default, so the real gap was that a student pasting exact assignment wording ("Solve for x: 3x - 7 = 20", numbered problem parts, "show your work") could still pressure the model into computing the result. A same-shape classification call already existed as a working pattern (`app/retrieval/relevance.py`, Decision 016), so this reuses it rather than introducing a new mechanism: one `generate_structured` call classifies `is_assignment: bool`, and when true, an added prompt block explicitly forbids stating the final answer or result even if asked directly, while still letting the tutor name what it noticed and walk through the first step.

## Impact

* One additional classification call runs on every `/tutor/ask` request, issued concurrently with retrieval (`asyncio.gather`) so it does not add latency on the critical path.
* This is advisory/soft, not a hard gate -- there is no separate "assignment mode" UI state, no blocked requests, and no persistence of the classification result. If it under- or over-fires in practice, the fix is prompt/classification tuning, not new architecture.
* True strategy selection (a distinct assignment-handling strategy, not just a stronger default-strategy prompt) remains M1 work, consistent with the scope already noted in `generation.py` and `router.py`.

## Update (2026-08-25, same day)

Real usage surfaced a classification gap the initial signal list missed: a student pasted a self-contained word-problem scenario verbatim ("At the malt shop the ratio of hotdogs sold to hamburgers sold was 6:8. For every 8 hamburgers sold there were 6 hotdogs sold") with no question mark and none of the original trigger phrases ("solve for", "homework", "show your work"). `detect_assignment` returned `False`, so the assignment notice never fired, and the generation model -- with no instruction to stay anchored to the given numbers -- improvised an unrelated scenario ("if they sold 16 hamburgers on Monday...") that the student then had to call out as not being their actual question.

`CLASSIFICATION_PROMPT` now explicitly names this shape -- a named setting plus specific numbers stated as fact rather than asked as a question -- as an assignment signal in its own right, with the absence of a question mark on a scenario like that treated as a signal rather than a reason to say no. It also explicitly carves out bare short replies (a lone number like `"4"`, answering a question already in play) as *not* a fresh assignment paste, since those are guided-discovery answers, not new pasted problems, and misclassifying them would trigger the assignment notice on every correct answer mid-conversation. Re-verified against a 13-case regression set spanning both the original cases and this failure mode: 0 mismatches. The full pytest suite (8 tests) still passes.

---

# Decision 018

**Date:** 2026-08-25

## Decision

Photo/PDF attachment is implemented as a transcribe-then-confirm flow, not as direct image input to generation. A new `POST /tutor/transcribe` endpoint (`app/tutoring/attachments.py`, `LLMClient.transcribe_document`) accepts an image or PDF, transcribes it to plain text via a single Claude call instructed only to transcribe and never to solve, and returns that text to the frontend, which populates the existing chat textarea (editable, not auto-sent) rather than submitting anything automatically. The uploaded file itself is never persisted -- it exists only in request memory for the duration of the transcription call. `POST /tutor/ask` is completely unchanged.

## Reason

Feeding an image directly into generation would let an attached photo skip retrieval, confidence gating, and assignment detection entirely -- a direct violation of Principle 5 (assignment likelihood and curriculum evidence must be decided before generation) and Principle 6 (retrieval before generation), and it would make photo-based questions invisible to the conversation log (no text representation of what was actually asked). Converting the attachment to text at the edge instead means every existing pipeline stage -- retrieval, the Decision 016 relevance fallback, Decision 017 assignment detection, guided-discovery generation -- runs on it completely unchanged, which is Principle 15 (extend without redesign) applied directly. Showing the transcription back to the student before sending, rather than auto-submitting, catches OCR misreads before they corrupt a guided-discovery thread (a misread "3x - 1 = 20" instead of "3x - 7 = 20" would otherwise silently produce a wrong answer) and is more honest about what the system actually read. Not persisting the file at all sidesteps a real product/privacy question this early: these are minors' photographed homework, sometimes with names or school info visible, and there is no product requirement yet that justifies storing them.

## Impact

* New dependency: `python-multipart` (required by FastAPI's `UploadFile` form parsing).
* `LLMClient` gained a fourth method, `transcribe_document(data, media_type, prompt)`, alongside `generate_structured` and `generate_text`. Any future second LLM provider adapter must implement it too.
* Verified end-to-end in a real browser (Chrome via Playwright, since Playwright's bundled Chromium build does not support this machine's macOS/arch combination): login, attach a real PDF, confirm the transcribed text matches the source exactly, submit, and confirm the assignment-detection notice from Decision 017 fires correctly on the transcribed text with no special-casing needed anywhere in the pipeline.
* Allowed types (JPEG/PNG/WEBP/PDF) and the 10MB size cap live in `Settings` (Principle 7 -- configuration over hard coding), not hard-coded in the route.
* HEIC (the default format on iPhone camera captures) is not in the accepted list -- Claude's vision input does not support it directly. Out of scope for this pass; would need either frontend-side conversion or relying on the browser's own HEIC-to-JPEG conversion on upload, which is not guaranteed across browsers.

## Update (2026-08-25, same day)

Real usage found a gap: `transcribe_document` unconditionally produced text for whatever image was uploaded, with no check that it was assignment content at all. A student attached an unrelated photo (a construction site layout) and got a plain description of it transcribed straight into the question box -- silently, since a 200 response always populated the textarea.

`transcribe_document`'s signature changed to return a structured result instead of plain text (`schema: type[SchemaT]`, matching `generate_structured`'s forced-tool-call pattern, now combined with the attachment content block). `app/tutoring/attachments.py` uses this with a new `AttachmentTranscription { is_assignment_content: bool, text: str }` schema and prompt: judge first, transcribe only if it's genuinely assignment/worksheet content. `transcribe_upload` now returns `None` when it isn't, and `POST /tutor/transcribe` turns that into a 422 with a clear message -- which the frontend's existing error-handling path already displays without ever calling `setQuestion`, so no frontend change was needed to fix "why did it print in the textbox."

This is deliberately not a subject-match check (science vs. math) -- that's a different, already-handled problem: the retrieval confidence gate (Decision 016) already tells a student "I don't have curriculum material for that" once valid transcribed text reaches `/tutor/ask`. This fix is narrower: reject content that was never an assignment or worksheet in the first place, before it reaches the pipeline at all. Verified against the real Anthropic API with a synthetic irrelevant PDF (a site-plan-style document) -- correctly rejected with 422 -- alongside a real worksheet PDF as a control, confirmed still working. New unit coverage in `tests/test_attachments.py`; full suite (22 tests) passes.

---

# Decision 019

**Date:** 2026-08-25

## Decision

Guided discovery now escalates when a student is genuinely stuck. A conversation carries a small persisted state (`conversations.tutoring_phase`, `struggle_count`, `confirm_count`, added by migration `20260825000000_conversation_tutoring_state.sql`) plus a new per-turn correctness classification (`app/tutoring/correctness.py`, same `generate_structured` pattern as Decisions 016/017). A pure state machine (`app/tutoring/escalation.py`) turns the current state and the classification into one of five generation strategies: `guiding` (default), `explain` (triggered on the 3rd consecutive incorrect answer -- full step-by-step solution, then one confirm question), `confirm_question` (next confirm question after a correct one), `confirm_retry` (re-explain briefly and re-ask on an incorrect or unclear confirm answer, without advancing), and `confirm_wrapup` (after the 3rd correct confirm answer, closes out and returns to guiding). This applies to every guided-discovery conversation, not only assignment-flagged ones. Word document (`.docx`) attachments were added alongside this, extracted mechanically with `python-docx` rather than through the vision LLM call images/PDFs use, since it's already digital text.

## Reason

This closes a gap flagged as far back as Decision 015/017's own code comments ("hint escalation to full direct explanation... still M1 work") and directly matches Principle 5 (architecture-principles.md): tutoring mode and learning strategy are supposed to be decided *before* generation, as explicit pipeline steps, not folded into one always-on prompt with a single success-only exit rule. Before this decision, a student who couldn't get a guiding question right had no designed behavior at all -- whatever the model improvised, indefinitely. It also fixes a reliability issue in the existing "3 correct answers -> wrap up" pattern: judging correctness had been done implicitly, inside the same call that writes the tutoring response, by having the model re-read the raw transcript -- fragile enough that it had already caused a real misjudgment (the malt-shop conversation losing track of whether "4" was a correct answer). A dedicated classification call, run as its own step and used to drive a small explicit state machine, is the same fix pattern already validated for retrieval confidence (Decision 016) and assignment detection (Decision 017), applied to a third judgment call the pipeline needs to make.

## Impact

* New dependency: `python-docx`.
* `conversations` gained three columns (`tutoring_phase`, `struggle_count`, `confirm_count`); existing rows default to `'guiding'`/0/0, so this is additive and backward-compatible.
* One additional classification call (`classify_answer`) runs per turn, but only when there's a prior assistant message to judge the student's answer against -- skipped entirely on a conversation's first message and on the low-confidence fallback path, so it doesn't fire on every request.
* Verified end-to-end against the real database and real LLM, not just unit tests: drove a live conversation through three wrong answers -> confirmed `tutoring_phase` flipped to `confirming` with counters reset -> gave a genuinely wrong confirm answer and confirmed `confirm_retry` neither advanced the counter nor falsely praised the answer -> drove three correct confirm answers -> confirmed wrap-up and a return to `('guiding', 0, 0)`. The state machine itself also has full unit coverage (`tests/test_escalation.py`) independent of any LLM call.
* The "3 correct -> wrap up" success path inside the default `guiding` prompt was deliberately left as-is (still model-inferred from the transcript, not classifier-driven) -- only the previously-undefined failure path was in scope for this pass.
* One real prompt-adherence edge case surfaced during verification and was left as a known limitation rather than chased further: an ambiguous non-answer (literally the word "correct", not an actual answer) was correctly classified as not-correct and correctly did not advance the counter, but the generation model's tone in that specific case read as more affirming than the `confirm_retry` prompt intends. Confirmed via a second test with a genuinely wrong numeric answer that the strategy behaves correctly (no false praise) in the case that actually matters; a real student is very unlikely to type a bare non-answer like "correct" as their attempt.

---

# Decision 020

**Date:** 2026-08-26

## Decision

The Grade 6 math corpus was expanded from 2 narrow slices (Module 1 and Module 4, "Module Overview and Topic A" only, ~40 pages) to the complete Eureka Math Grade 6 curriculum: all 6 modules, ingested at topic granularity (27 `curriculum_resources` rows across 6 module-level concepts, one row per topic rather than one per module) so citations stay specific ("Topic C: Unit Rates," not a single title spanning 250 pages). Concepts remain at the module level; retrieval doesn't filter by concept (`app/retrieval/store.py` filters only on subject and grade band), so the finer split is purely for accurate per-topic titles and standards, not a retrieval-quality change.

## Reason

Page ranges and Common Core codes were not guessed -- each module's own table of contents lists exact printed page numbers and standard codes per topic (verified directly from the downloaded PDFs), and a per-module printed-page-to-PDF-page offset was independently confirmed for each of the 6 modules before computing ranges, catching that Module 1 uses a different front-matter length (offset 3) than Modules 2-6 (offset 0). This is what let the ingestion be accurate rather than approximate.

## Impact

* 1,414 total chunks (up from 54) across math and science combined; math alone grew from 2 resources/36 chunks to 27 resources/~1,396 chunks.
* Two real bugs were caught and fixed during this work, not shipped silently:
  1. A duplicate-ingestion incident: an earlier command that appeared to time out at the harness's 2-minute limit had not actually killed its underlying process, which kept running as an orphan and overlapped with a second, deliberately backgrounded run, double-inserting several early resources. Caught by comparing actual resource counts per concept against the expected count, fixed with a SQL de-duplication pass (`row_number() over (partition by concept_id, title order by id)`), and re-verified at zero duplicates afterward.
  2. A retrieval confidence gap: with ~40x more content, "how do I simplify a ratio" scored `band: high` (0.529 similarity) against completely unrelated content (Module 4, Solving Equations), and the generation model answered anyway from its own outside knowledge -- undetected because the relevance-check fallback (Decision 016) only runs on the `low` band. This is a real, currently-unresolved gap in the confidence-gating design, not something this decision fixes; measured cost of closing it (running the relevance check on every request) is documented separately.
* `scripts/ingest_content.py`'s PDF loader was changed to cache the downloaded `pypdf.PdfReader` per URL for the life of the process, since 27 topic-level entries across 6 modules meant several topics sharing the same module PDF -- without caching, Module 4's file alone would have been re-downloaded 8 times in one run.
* Confirmed live and not just via chunk counts: retrieval for "how do I find the mean absolute deviation" and "how do I divide a fraction by a fraction" -- both genuinely new content -- now returns the correct topic with high, accurate confidence (0.636 and 0.639 respectively).

---

# Decision 021

**Date:** 2026-08-26

## Decision

The Grade 6 science corpus was expanded from 2 CK-12 chapters (Cell Biology, Ecology) to 12: the 10 remaining chapters of CK-12's "Life Science for Middle School" (via K12 LibreTexts) were added -- Introduction to Life Science, Genetics and Molecular Biology, Evolution, Viruses and Bacteria, Protists and Fungi, Plants, Animals, Invertebrates, Vertebrates, and Human Body Systems -- with one deliberate content exclusion: Chapter 11's reproductive health/puberty unit (sections 11.64-11.78: reproductive systems, menstrual cycle, pregnancy, STIs) was left out.

## Reason

The reproductive health unit is a different category of content from the rest of the corpus, not a difficulty or curriculum-fit question. Schools typically handle this topic with separate permission structures (opt-in health curricula, parental consent), not casual retrieval alongside general biology, and this project has no such consent mechanism. Excluding it was a deliberate, explicit content-policy decision, confirmed with the user before ingesting, not a default applied silently. Everything else in Chapter 11 (skeletal, digestive, cardiovascular, respiratory, nervous, immune systems) was ingested normally, since it's ordinary middle-school life science content with no comparable sensitivity.

## Impact

* 1,716 total chunks (up from 1,414 after Decision 020) across math and science combined; science alone grew from 2 resources/18 chunks to 12 resources/~338 chunks.
* The exclusion boundary (sections 11.64-11.78) was verified twice: once structurally (the section-numbering filter itself, after catching and fixing a bug where naive float parsing collided "11.7: Bone Health" with "11.70: Menstrual Cycle" since both parse to `11.7` as a float -- fixed by parsing chapter and section as separate integers), and once empirically after ingestion (keyword search across the ingested Human Body Systems chunks for menstrual/pregnancy/sperm/puberty/etc. terms, confirming zero matches beyond incidental, appropriate mentions -- e.g. pregnant women's iron needs in a nutrition chunk, pregnancy as a flu-vaccination risk factor -- and one harmless artifact, a bare LibreTexts "next page" navigation label that leaked into one chunk's text with no actual content behind it).
* This is a chapter-level exclusion from one specific book, not a general content-safety policy -- if science coverage expands to a different source later, this same judgment call (what's appropriate for unsupervised retrieval vs. what needs separate handling) will need to be made again, not assumed inherited.
* `scripts/ingest_content.py`'s raw `psycopg.connect()` call was missing the `prepare_threshold=None` fix that `app/db.py`'s pool already carries for Supabase's transaction-mode pooler (Decision 019's connection-pool work implicitly, though never backported to this script) -- it failed immediately on the first resource of this run with `DuplicatePreparedStatement`, was caught before any partial data committed, and fixed to match the app's existing pattern.
* This book ("Life Science for Middle School") is not grade-6-specific -- NGSS bands standards across grades 6-8 rather than assigning them to a single year, and CK-12 itself scopes the book to "middle school," not Grade 6. Labeling it `grade_band: 6` is a simplification inherited from Decision 013's original source choice, not a new claim introduced here.

---

# Decision 022

**Date:** 2026-08-26

## Decision

A content-safety guardrail now gates every request, closing a gap named in the original proposal's Section 4.2 ("the guardrail layer will check requests for personally identifiable information, prompt injection attempts, and unsafe content") but never built. A new `check_safety` node runs first in the LangGraph pipeline (`app/tutoring/safety.py`, same structured-classification pattern as Decisions 016/017/019), classifying every question into one of six categories: `none`, `prompt_injection`, `unsafe_content`, `crisis`, `sensitive_topic`, or `pii`. Three categories short-circuit the normal tutoring response (`prompt_injection`, `unsafe_content`, `crisis`); the other two (`sensitive_topic`, `pii`) let the pipeline run exactly as before. Every non-`none` classification is persisted to a new `flagged_interactions` table regardless of whether it blocked, so nothing is thrown away before Pillar B's guardian dashboard exists to read it.

## Reason

This was prompted by a real incident, not a hypothetical: a student's "how do people reproduce" was answered from genuinely grounded genetics content (Decision 021 only excluded one chapter's dedicated reproductive-health unit; adjacent chromosome content in a different, non-excluded chapter still covered it), and a follow-up was correctly declined for lack of evidence. Both individual responses were correct given how the system is designed, but nothing looked at the question's *intent* before deciding whether to search for an answer -- content exclusion is a coverage accident, not a safety mechanism. Classification and blocking policy are deliberately kept separate (`should_block`/`response_for` are plain lookups, not part of the model's judgment) so a legitimate curriculum question about a sensitive topic still gets taught, just made visible to a guardian, rather than refused outright -- refusing every sensitive-adjacent question would be both unhelpful and inconsistent with "teach the student, don't just gate them."

`crisis` was split out from `unsafe_content` after testing surfaced a real problem before this shipped: a self-harm disclosure ("I have been feeling really sad and thinking about hurting myself") was initially classified the same as a bomb-making request, so both got the identical flat "I can't help with that" decline. That is not an acceptable response to an actual crisis disclosure. `crisis` now gets its own compassionate response naming real resources (988 Suicide & Crisis Lifeline, Crisis Text Line) and urging the student to talk to a trusted adult, verified to trigger correctly on both self-harm and abuse-disclosure phrasing.

## Impact

* New table `flagged_interactions` (student, conversation, category, question, blocked, timestamp). Per Decision 009, guardians get no direct RLS access to it -- only the student can read their own rows; guardian visibility is deferred to a backend-mediated summary when Pillar B's dashboard is built, not raw table access.
* `check_safety` is the new single entry point of the LangGraph pipeline; on a blocking category it routes straight to `END` via a conditional edge returning multiple possible destinations (`["retrieve", "detect_assignment"]` or `END`), one more real branch on top of the ones already there (Decision 006's originally-named "safety check" node, built four decisions later than the rest).
* Verified against the real Anthropic API across 8 cases (ordinary questions, prompt injection two ways, a bomb-making request, PII sharing, a genuine sensitive-but-legitimate question, a self-harm disclosure, and an abuse disclosure) -- all classified correctly. Verified live end-to-end through the real HTTP API: a normal question streams unaffected and creates no flag row, a prompt-injection attempt blocks with the generic decline, a crisis disclosure blocks with the compassionate/resource message, and assignment detection continues working unaffected by the new gating node. Full pytest suite (29 tests, 7 new) passes.
* One deliberately out-of-scope note: `sensitive_topic` and `pii` are recorded but not yet surfaced anywhere a human would see them -- that's Pillar B, sequenced later per the roadmap.

## Update (2026-08-26, same day)

Real usage surfaced a rough edge in the non-blocking path: a student asked "how is sex done," which correctly classified as `sensitive_topic` (non-blocking) and correctly got flagged, but retrieval found no matching content and returned the ordinary `NO_EVIDENCE_MESSAGE` ("try asking about ratios, unit rates..."). That's a tone-deaf response to a sensitive question, even though every individual piece of the pipeline did what it was supposed to.

`app/tutoring/safety.py` gained `SENSITIVE_NO_EVIDENCE_MESSAGE`, a warmer redirect to a parent, teacher, or trusted adult. The router now shows this instead of the generic subject-menu fallback specifically when `safety_category == "sensitive_topic"` and retrieval band is `low` -- narrow and deliberate: this does not touch the `pii` category (a different concern, sharing information, not an off-limits topic) or change behavior at all when real curriculum content exists for a sensitive-but-covered question (e.g. "how do people reproduce," which still answers from genuine genetics content, per the original incident this whole decision responds to). Verified live: the exact reported case now gets the redirect, and a genuinely off-topic control question ("how do I bake a cake") is unaffected. Full suite still passes (29 tests).

---

# Decision 023

**Date:** 2026-08-26

## Decision

Every tutoring turn now persists a decision trace: which safety category it was classified into, the retrieval confidence band, the evidence chunk IDs actually used, whether it was flagged as an assignment, its correctness classification, the chosen struggle-escalation strategy, and the tutoring-phase/struggle-count/confirm-count state transition. `app/observability/traces.py`'s `record_decision_trace()` writes one row to a new `decision_traces` table from `app/tutoring/router.py`'s `ask()` endpoint, after each of the three response branches (safety-blocked, low-confidence fallback, normal grounded generation).

## Reason

This is Pillar C, Option S from the post-proposal-gap-analysis roadmap: "no new intelligence, just stop throwing away data that's already there." Every field this writes was already computed by the LangGraph pipeline or the router on every single request and discarded the moment the response finished streaming. This unblocks Pillar C-M (aggregate metrics: hint dependency, repeated confusion, retrieval confidence trends) and, downstream of that, Pillar B-L (the full parent/teacher dashboard) -- neither can exist without a historical record of what the tutor actually decided, turn by turn. Per `app/observability/__init__.py`'s original docstring and Decision 009's RLS principle, this table is admin-only: RLS is enabled with zero select or insert policies for any client role, so neither the student nor a guardian can read it directly -- only the backend's own privileged connection can.

## Impact

* New table `decision_traces` (conversation, student, question, safety_category, band, strategy, is_assignment, evidence_chunk_ids, correctness, tutoring_phase_before/after, struggle_count_before/after, confirm_count_before/after, timestamp). No select or insert policy exists for it at all -- stricter than `flagged_interactions`, which at least lets the student read their own rows.
* The three response branches populate the trace differently since the graph short-circuits before running every node: a safety-blocked turn never ran retrieval or assignment detection, so `band`, `strategy`, `is_assignment`, `correctness`, and evidence are all `None`/empty; a low-confidence turn ran assignment detection in parallel with retrieval so `is_assignment` is populated but there's no evidence or strategy; only a normal high-confidence turn populates every field, including the actual chunk IDs passed to generation.
* Full pytest suite passes unchanged (29 tests -- this is pure persistence, no new branching logic to unit-test). Verified live against the real running backend and a real, disposable Supabase auth user (created via the admin API, deleted afterward along with its cascaded profile/conversation/trace rows): sent one crisis question, one off-topic question, and one real "what is a ratio?" question, then queried `decision_traces` directly and confirmed all three rows had exactly the expected field values for their branch -- including the normal-path row carrying its three real evidence chunk UUIDs and `strategy: guiding`.
