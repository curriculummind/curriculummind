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

---

# Decision 024

**Date:** 2026-09-21

## Decision

A guardian links to a student through a teacher-issued class code, not the parent-invite-by-email flow originally discussed for Pillar B-L. `profiles.class_code` is a unique column, generated server-side for a teacher at signup and enforced by a database check constraint to exist only for teacher rows. A student redeeming one at their own signup gets their `profiles` row and the resulting `guardian_links` row inserted in the same transaction as one another -- a bad code creates nothing at all.

## Reason

A parent-invite-by-email flow needs real email deliverability (a transactional email provider, domain verification, DNS records) that this project has not built and isn't ready to commit to yet. A classroom pilot gets institutional adult oversight "for free" through the teacher relationship, without needing to solve that delivery problem first. `guardian_links` was already schema-generic over guardian/teacher (Decision 009 named both), so this doesn't add a new table or a new access model -- it just supplies the first real way to populate a table that has existed, unused, since the initial migration. Parent-invite is deferred, not abandoned; it can be added later as a second way to populate the same `guardian_links` table without changing this one.

## Impact

* New migration: `profiles.class_code` (unique, nullable, `check ((role = 'teacher') = (class_code is not null))`). No new RLS policy -- the existing owner-only `profiles` policies already cover the column.
* `ProfileCreate` gained validation: `class_code` is required (and normalized to uppercase) for `role: "student"`, forbidden for `teacher`/`guardian`.
* Signup's email-confirmation path now carries `role`/`display_name`/`grade_level`/`class_code` through Supabase Auth's `user_metadata`, since the login page's deferred profile-creation fallback previously hardcoded `role: "student"` -- safe when only students existed, not once teachers do.
* Verified live: a wrong class code returns `400` with no profile row created at all; the real code returns `201` and exactly one `guardian_links` row (`status: 'active'`).

---

# Decision 025

**Date:** 2026-09-21

## Decision

Guardian-facing notifications (mastery milestone, repeated struggle, assignment-leaning pattern, sensitive-topic notice) are computed event-driven, in-process, via a FastAPI `BackgroundTask` scheduled at the end of `/tutor/ask` -- not a separate worker process, and not email. A fifth type shown in the original mockup, a weekly digest, is deferred along with email entirely.

## Reason

Decision 007 already established that an alert should fire from a deterministic threshold over accumulated evidence, not an LLM's in-the-moment judgment -- this satisfies that without requiring new deploy infrastructure. No background worker process exists anywhere in this codebase yet (`app/evaluation/__init__.py` was, until now, only an aspirational docstring); standing one up now, before there's a second reason to need one, would be scope well beyond what this feature requires. A weekly digest is inherently calendar-driven, not event-driven, and needs a scheduler either way -- deferred together with email rather than half-built now.

## Impact

* New table `notifications` (student_id, category, message, timestamp), admin-write / guardian-read RLS -- same posture as `decision_traces`, gated on an *active* `guardian_links` row so a revoked link stops seeing new alerts.
* Crossing detection (exactly 3, not >=) in `app/evaluation/notifications.py`, so a sustained streak doesn't re-fire the same alert every subsequent turn; a `sensitive_topic`-category hit fires immediately every time with no streak, since a single occurrence is inherently notable on its own.
* All five of Decision 022's safety categories map to the single `sensitive_topic` notifications category (for icon/styling), but message wording is written per actual category -- a `crisis` flag reads noticeably more urgent than an ordinary `sensitive_topic` hit, deliberately not treated the same.
* Because `/tutor/ask` returns a hand-built `StreamingResponse` rather than a plain return value, `BackgroundTasks` is not auto-attached by FastAPI and must be assigned to `response.background` explicitly -- confirmed live, not just assumed, since a silent miss here would mean the feature never fires at all.
* New router `app/evaluation/router.py` (`/guardian/roster`, `/guardian/students/{id}/progress`, `/guardian/students/{id}/mastery-curve`, `/guardian/notifications`), reusing `get_topic_progress`/`get_mastery_curve` from `app/tutoring/progress.py` directly rather than re-deriving the mastery computation for a second audience.

---

# Decision 026

**Date:** 2026-09-22

## Decision

The tutoring graph's `retrieve` node searches with the bare question first. It only retries once, with the history-augmented `retrieval_query`, if the bare-question search finds nothing the relevance check accepts -- reversing the previous default of always searching with history concatenated on.

## Reason

The history concatenation in `_build_retrieval_query` (Pillar D, Decision 020's follow-up) exists to rescue a short, context-free follow-up ("3", "is that right?") that has no topic keywords of its own. But it actively breaks the opposite case: a genuine topic switch. Reported and reproduced live -- "generate an image of a cell and label its parts," asked right after an unrelated genetics question in the same conversation, retrieved zero relevant candidates when embedded together with the tutor's own genetics answer (which dominated the embedding), even though the same question asked as a fresh conversation retrieved and answered correctly. The student got the generic "I don't have curriculum material" fallback for a topic the corpus genuinely covers. Trying the bare question first fixes the topic-switch case for free in the common case (no retry needed) and preserves the original short-follow-up rescue as a fallback, rather than picking one case to break.

## Impact

* New graph node `retry_with_history` (a trivial state flip, `used_augmented_query: True`) and a loop-back edge from `relevance_check` to `retrieve`, bounded to fire at most once per turn (`_route_after_relevance_check` only routes there when `used_augmented_query` isn't already set, and skips it entirely on turn 1 where `retrieval_query == question` and a retry would just repeat the same search).
* `_retrieve_node` now records which query it actually searched with (`effective_query`); `_relevance_check_node`'s LLM judgment uses that instead of always `retrieval_query`, so the judgment matches the evidence it's actually being asked about even after a retry.
* Verified live, both directions on the same fix: the genetics-then-cell-image case now gets a real, grounded answer ("I can't generate images, but here's how to draw your own labeled diagram... animal or plant cell?"); a short "2:3" follow-up to an unrelated-sounding recipe-ratio question still retrieves and answers correctly via the augmented-query fallback, confirming the original rescue case wasn't regressed. Full pytest suite unaffected (61 tests -- this graph has no existing unit tests, being async/DB-dependent; covered by live verification instead, consistent with how the rest of the graph has always been tested).

---

# Decision 027

**Date:** 2026-09-22

## Decision

The tutor shows a real curriculum diagram inline in chat when one exists for the evidence being used, instead of only ever describing content in text -- science only, and only for the Cell Biology concept in this first pass. A new `resource_images` table links a real, backfilled image to a `curriculum_resources` row and the specific CK-12 lesson page it came from; a `curriculum-images` Supabase Storage bucket holds the actual bytes, re-hosted rather than hotlinked.

## Reason

Investigated after a student asked the tutor to "generate an image of a cell and label its parts" and got a generic capability-limit response. No image-generation model exists in this stack, and adding one is a separate vendor/cost decision, deliberately not made here. But the ingestion pipeline already discards every image in the source material -- both extraction paths (pypdf for PDF, BeautifulSoup's `.get_text()` for HTML) keep text only. Direct inspection found this split cleanly by subject: the EngageNY math PDFs have no usable diagrams at all (what pypdf reports as "images" are a repeated background texture or rasterized equation-typesetting fragments; real diagrams are either absent or literally blank "draw this yourself" worksheet prompts), while the CK-12 science HTML pages have genuine, well-labeled diagrams with descriptive alt text and stable CDN URLs. This is science-only by fact, not by choice.

Attribution is at the resource level, not the chunk level, because science ingestion aggregates many CK-12 lesson pages into one `curriculum_resources` row per concept with no page-boundary metadata retained per chunk (`chunk_text()` just flatly packs paragraphs). Retrofitting an exact chunk-to-page mapping onto *existing* `document_chunks` rows would be fragile -- a silent wrong-image match is worse than a coarser but honest granularity -- and re-ingesting fresh would orphan `decision_traces.evidence_chunk_ids`, which joins through `document_chunks.id` for the mastery-tier computation (Pillar C-M). A new table, touching no existing row, avoids both risks.

Scope is deliberately narrow (Cell Biology's 6 lesson pages, not all 11 science concepts): the image-selection heuristic (`pick_best_image`, scoring keyword overlap between the evidence chunk and each candidate image's caption/page-title, since a resource can bundle several lesson pages each with its own image) is new and unproven. Proving it on one already-spot-checked concept before trusting it across ~190 pages is the same incremental-vertical-slice posture as every other feature this project has shipped. Extending later is re-running the backfill script against more `RESOURCES` entries, not a redesign.

The Storage bucket is public-read, not gated behind signed URLs: the source images are already hosted on CK-12's own public CDN today, so re-hosting them publicly exposes nothing that isn't already public -- it only moves who serves the bytes, onto infrastructure this project controls instead of a third party's.

## Impact

* New table `resource_images` (resource_id, source_page_path, source_page_title, image_url, public_url, caption, license, attribution), same RLS posture as `curriculum_resources`/`document_chunks` (authenticated-read, backend-only write).
* New Storage bucket `curriculum-images`, public read, uploaded via the existing `supabase-py` dependency (already used in `app/identity/auth.py`) -- no new dependency.
* New standalone script `backend/scripts/backfill_resource_images.py`, separate from and never entangled with `ingest_content.py`'s own ingestion flow, re-runnable (`on conflict (resource_id, source_page_path) do update`). Reuses `ingest_content.py`'s `RESOURCES`/`LIBRETEXTS_BASE`/`BROWSER_HEADERS` rather than re-declaring the source list.
* `RetrievedChunk` gained `resource_id` (populated from `search_chunks`' existing `curriculum_resources` join, previously selected but not exposed on the model).
* `/tutor/ask` gained `X-Evidence-Image-Url`/`-Caption`/`-Attribution` response headers, following the exact existing `X-Citation-Code`/`X-Citation-Framework` pattern -- percent-encoded, unlike the citation headers, since caption/attribution are free text from third-party alt attributes rather than short ASCII codes. Math questions never populate `resource_images` rows, so the header is naturally absent with no subject branching needed in the router.
* Verified live: backfilled all 6 Cell Biology pages, confirmed each image is a genuinely different, correctly captioned diagram (onion cells, organelles, plasma membrane, nucleus, organelles again, plant cell -- two pages legitimately share CK-12's own reused organelles diagram, confirmed by matching file size, not a bug) and every `public_url` is directly fetchable. Filtering needed one iteration live: the first real page (`2.18: Cell Theory`) revealed CK-12's own logo/license-badge images weren't caught by the initial decorative-image filter (only LibreTexts' site logo was) -- fixed and re-verified before trusting the rest of the backfill.
* Generation prompts (`app/tutoring/generation.py`) are unchanged -- the image is a UI-layer addition, not something the model is told about or asked to reference.

---

# Decision 028

**Date:** 2026-09-28

## Decision

Clicking a topic in the chat sidebar now narrows retrieval to that one curriculum resource for subsequent questions, until deselected. Clicking the same topic again clears the focus. Previously the click only relabeled the header (`selectedTopic` fed nothing into `/tutor/ask`) -- it looked interactive but had zero effect on what the tutor actually retrieved or discussed.

## Reason

Reported directly: the topic rows are visibly clickable (hover state, highlight on select) but clicking one did nothing a student could actually observe in the conversation. That's worse than not being clickable at all, since it implies a focus that isn't real. Two fixes were on the table -- make it functional, or strip the click affordance entirely -- and functional was chosen because the plumbing already existed: `search_chunks` already had an unused `concept_slug` filter built for exactly this kind of narrowing (Decision 016-era), so adding a `resource_id` filter alongside it was a small, well-understood extension, not new architecture. Scoping to the *conversation's* retrieval rather than opening a separate per-topic chat matches the existing "one continuous conversation per subject" model (conversation resume, no "new chat" concept) -- a topic click changes what the ongoing conversation is currently focused on, it doesn't fork a new thread.

Deliberately no unscoped fallback when a focused question finds nothing in the selected topic: a student who explicitly narrowed to a topic and then asks something unrelated should be told that plainly, not silently answered from a different topic's content, per Decision 026's same "grounded, not generated" posture.

Topic-level mastery tracking needed no changes at all -- it was already computed from which evidence chunks actually got used per turn (`progress.py`), independent of any UI selection state, so "chapterwise completions are tracked" was already true before this fix.

## Impact

* `search_chunks` (`app/retrieval/store.py`) and `retrieve` (`app/retrieval/pipeline.py`) gained an optional `resource_id` filter, applied identically to the existing `concept_slug` filter.
* `TutoringState` gained `topic_resource_id`; `_retrieve_node` passes it through on both the bare-question and history-augmented-retry passes (Decision 026), so a topic focus survives the retry.
* `AskRequest` gained `topic_resource_id: str | None`; the frontend sends `selectedTopic?.resourceId` on every turn.
* `chat-client.tsx`'s topic-select handler is now a toggle (`prev?.resourceId === topic.resourceId ? null : topic`), and a "Focused · clear" chip appears in the chat header when active, both confirming the state and giving an explicit way to clear it beyond re-clicking the same sidebar row.
* Verified live, mechanically, not just by eyeballing generated prose: the same query embedding run through `search_chunks` unscoped pulled candidates from 5 different resources; scoped to a `resource_id`, all 15 returned candidates matched that resource exactly.

---

# Decision 029

**Date:** 2026-09-28

## Decision

A conversation can now be scoped to a specific topic (`conversations.topic_resource_id`, nullable), not just a subject. Selecting a sidebar topic resumes (or starts) a separate conversation for that topic specifically; switching to a different topic shows a blank thread instead of the previous topic's unrelated history; switching back resumes exactly where that topic's own thread left off. `null` still means the general, unfocused conversation per subject -- today's existing behavior, unchanged for a student who never selects a topic.

## Reason

Immediate follow-up to Decision 028: retrieval scoping alone wasn't enough. Reported directly -- selecting a different topic left the old, unrelated conversation on screen with no visible change, which read as "the click still does nothing." A purely cosmetic fix (just clearing the displayed messages) was considered and rejected: the backend still loads full conversation history for every turn, uses the last assistant message to judge correctness, and falls back to recent history when a bare question doesn't retrieve well -- if the screen reset but the backend didn't, a student's first answer under a new topic could get judged against a question they can no longer see. The reset has to be real on both sides, or not claimed at all.

This deliberately extends "one continuous conversation per subject" (the resume model built for conversation persistence) to "one continuous conversation per subject-topic pair," rather than replacing it -- the general, unfocused conversation still works exactly as before. Confirmed the change doesn't touch the actual latency bottleneck (LLM round-trips in the decision pipeline, per the earlier speed investigation) before starting: this is bookkeeping on which conversation row a message belongs to, not a new API call anywhere in the hot path -- if anything, per-conversation history reads get smaller over time as threads split by topic instead of one subject-wide thread growing forever.

## Impact

* New nullable column `conversations.topic_resource_id`, referencing `curriculum_resources`. No RLS change -- the existing per-row "readable by their student" policy already covers it.
* `create_conversation` and `get_latest_conversation` (`app/tutoring/conversations.py`) both gained an optional `topic_resource_id` parameter; the latter matches `null` via `is not distinct from`, not `=`, since `=` never matches `NULL` in SQL and the general conversation's scope IS `null`.
* `/tutor/conversation` gained an optional `topic_resource_id` query param; `/tutor/ask`'s `AskRequest` already had one from Decision 028 and now also threads it into conversation creation, not just retrieval.
* `chat-client.tsx`'s history-loading effect now re-runs on `selectedTopic` changes, not just once on mount, clearing the displayed thread and tutoring-phase state before fetching the newly-scoped one.
* Verified live end to end, both at the API layer and in a real browser: asked a question focused on one topic, switched to an unrelated topic (blank thread, confirmed), switched back (exact same conversation id and message resumed, not a new one).

---

# Decision 030

**Date:** 2026-09-30

## Decision

The tutoring decision pipeline's four classification-only calls (safety check, assignment detection, relevance judgment, correctness classification) now run on a smaller, faster model (Haiku) instead of the same model used for the actual tutoring response. Generation and worksheet transcription stay on the full model.

## Reason

Reported directly, with two explicit constraints: fastest response possible, with no added cost, prioritizing consistency and performance. Measured the pipeline first (already timed per-node a few days earlier): classification is four sequential LLM round-trips before generation even starts, and none of them need generation-quality reasoning -- each is a narrow category or yes/no judgment. Splitting model by *role* (classify vs. generate) rather than uniformly using the strongest model everywhere is a pure win on both stated constraints: a smaller model is cheaper per call, not more, so latency improves without adding cost.

The real risk was "consistency," not architecture -- several of these exact prompts were hand-tuned this session to fix real accuracy bugs (Decision 016's relevance wording, the correctness classifier's `_last_question` fix, Decision 026's retrieval retry). A cheaper model could plausibly judge those same edge cases differently. Verified live before trusting this, not assumed: re-ran every one of the session's previously-fixed tricky cases -- crisis-language detection, PII, prompt injection, the "what is 2:3" notation-vs-literal-number relevance case, the genetics-then-cell-image retry case, a terse-but-correct numeric answer, and the reproduction-adjacent sensitive-topic case -- all nine produced the same behavior as the documented, previously-verified baseline. No regression found.

## Impact

* New setting `anthropic_classifier_model` (default `claude-haiku-4-5-20251001`), separate from `anthropic_model`.
* `/tutor/ask` now builds two `AnthropicLLMClient` instances instead of one: `classifier_llm` passed into `run_tutoring_pipeline` (reaches all four graph classification nodes automatically, since they already read a single `state["llm"]` uniformly -- zero changes needed in `graph.py` itself), `generation_llm` passed only to `generate_grounded_response`. Worksheet transcription (`/tutor/transcribe`) keeps its own separate full-model client unchanged -- accuracy-sensitive (reading a photographed assignment), and wasn't part of the four classification call sites this decision covers.
* Measured live, same 3-turn scenario timed a few days earlier (genetics -> cell-image -> follow-up, the exact case from the original latency report): pre-stream latency dropped from ~8.6s to ~6.2-6.5s per turn, roughly a quarter faster, with zero additional cost (a smaller classifier model is strictly cheaper, not more).
* Further latency ideas surfaced but deliberately not built yet, each flagged with its real tradeoff rather than assumed safe: skip the LLM relevance check entirely when top-similarity confidence is very high (biggest remaining lever, since relevance-check is still the single largest cost -- needs the same before/after accuracy verification rigor as this decision before shipping); prompt caching on the repeated boilerplate portion of each classification prompt (pure infrastructure, no quality risk, not yet implemented); parallelizing correctness classification with the front of the pipeline instead of gating it behind relevance check (now cheaper to accept than when first raised, since the wasted call on blocked/low-confidence turns is a Haiku call, not a full-model one -- still a real if small added cost, left as the user's call, not decided here); reducing the 15-candidate relevance pool -- explicitly rejected, since that count exists specifically because the correct chunk has ranked as low as 11th in this corpus (Decision 016/`store.py`'s own docstring).

---

# Decision 031

**Date:** 2026-09-30

## Decision

The struggle-escalation state machine (`app/tutoring/escalation.py`, Decision 019) is redesigned so a correct answer and an unclear answer both have a real path to ending a guided-discovery thread, not just a wrong answer. Separately, the correctness classifier (`app/tutoring/correctness.py`) now sees the full tutor message (anchor + question), not only the isolated question -- and correctness classification specifically stays on the full model rather than Decision 030's faster classifier, based on a measured reliability difference.

## Reason

Reported directly from a real 15-turn conversation that never reached an explanation, with an explicit spec: at most 3 follow-up questions on wrong answers, at least 1 more after a correct one, before explaining. Reading the actual state machine found the real bug: a correct answer in the "guiding" phase only ever reset `struggle_count` and looped in "guiding" -- there was no code path from "the student got it right" to "now explain," only from "the student got it wrong enough times." An "unclear" answer moved neither counter, so a student who kept answering vaguely also never escalated. And once escalated into "confirming", a wrong confirm answer always returned `confirm_retry` with no cap at all -- a second, different unbounded loop. All three were the same class of bug: only one branch of the whole state machine had the power to end a thread.

Fixing the counters immediately surfaced a second, deeper bug while verifying live: a textbook-correct answer ("1:2" to "write that ratio using smaller numbers") was being classified "unclear" -- on *both* Sonnet and Haiku, ruling out Decision 030 as the cause. The real issue: `_last_question()` (added to stop worked-example numbers in the anchor from being misread as part of the question) strips the anchor down to just the trailing question, which also throws away the antecedent a follow-up question routinely depends on ("that ratio" only makes sense with "3:6" still in view). The classifier literally could not resolve the reference. Fixed by passing both the full message and the isolated question, with the prompt explicit about which one is being judged.

With that fixed, a direct before/after comparison (10 trials, identical real case, both models) showed Haiku correct 9/10 times against Sonnet's 10/10 on the same cases -- not solid enough for the single judgment the entire escalation state machine runs on, where a wrong call doesn't just cost a little quality, it visibly breaks the tutoring flow (explaining something already understood, or looping past it). Kept correctness classification on the full model; safety/assignment/relevance stay on Haiku, all three independently re-verified at 100% consistent across the same nine cases checked for Decision 030.

## Impact

* `STRUGGLE_THRESHOLD` stays 3; `CONFIRM_THRESHOLD` changes from 3 to 2 (one correct answer moves "guiding" -> "confirming" and asks one more; a second consecutive correct one wraps up) -- both counters now checked identically regardless of current phase, and a non-correct answer during "confirming" now contributes to the same shared struggle budget instead of retrying forever.
* `_classify_correctness_node` (`app/tutoring/graph.py`) uses a new `correctness_llm` state field, separate from the `llm` field the other three classification nodes share; `run_tutoring_pipeline` takes an explicit `correctness_llm` parameter; `/tutor/ask` passes its `generation_llm` (the full model) for it, not `classifier_llm`.
* `backend/tests/test_escalation.py` rewritten -- the old tests asserted the bug as correct behavior (e.g. "a correct answer resets struggle count and keeps guiding" as the *expected* outcome); new tests cover both counters' caps, cross-phase struggle sharing, and that a correct/incorrect answer resets the other counter.
* Verified live end to end, both paths: two correct answers in a row (to what was actually asked, not just "obviously right" content) produced `confirm_question` then `confirm_wrapup`; three non-correct answers in a row (mixing "unclear" and "incorrect") produced `explain` on exactly the third, not before and not never.

---

# Decision 032

**Date:** 2026-10-06

## Decision

A real, re-runnable RAGAS-style offline evaluation harness now exists (`backend/scripts/run_evaluation.py`, metrics in `backend/app/rag_eval/`): a 22-case hand-curated golden set (`backend/scripts/evaluation/golden_set.py`) run through the actual, unmocked retrieval and generation pipeline, scored on context precision, context recall, faithfulness, and answer relevancy, with results committed to `docs/evaluation-report.md` and `backend/scripts/evaluation/results.json`.

## Reason

The proposal's gap analysis already named this plainly: a formal RAGAS-style evaluation report was the single most repeated, most explicit item across both proposal drafts, and the one true gap against a named success criterion. No golden set, harness, or `ragas`-equivalent dependency existed anywhere in the repo.

`ragas` itself wasn't adopted: it's built around LangChain chat models, and this stack's `LLMClient`/`EmbeddingClient` abstractions (Anthropic forced-tool-use structured output, a plain OpenAI embedding client) don't fit that shape. Reimplementing each metric's definition directly follows the same precedent Decision 016 already set for cross-encoder reranking -- same job, different mechanism. Three of the four metrics (precision, recall, faithfulness) became direct LLM-judge calls; answer relevancy keeps RAGAS's own published algorithm unchanged (reverse-engineer questions from the answer, embed, cosine-compare against the original question), since the embedding client it needs already existed for exactly this purpose.

Context precision deliberately reuses `is_actually_relevant` (`app/retrieval/relevance.py`) rather than writing a second, parallel relevance judgment -- it's already the exact question that metric asks. That reuse surfaced a real harness bug before this could ship: a first draft determined each case's confidence band from `retrieve()`'s raw similarity gate alone, and 3 of 4 deliberately out-of-corpus probes came back "high" -- the harness wasn't testing what students actually experience. The live pipeline's effective band isn't the raw gate, it's that gate as overridden by `_relevance_check_node`'s LLM judgment (Decision 016/Pillar D), which runs on every turn regardless of raw similarity. Fixed by sharing one set of relevance judgments between the band decision and the precision score (`judge_relevance`, `app/rag_eval/context_precision.py`), rather than asking the LLM about the same chunks twice. After the fix, all 4 fallback probes correctly triggered.

Running the fixed harness for real surfaced one genuine retrieval finding, left in the report rather than smoothed over: the `virus-vs-bacteria` case retrieved topically on-target candidates by raw similarity (0.48 top score, correct resource) that the relevance judge rejected outright -- the top chunks are CK-12 section-header outlines ("What is a Virus? Are Viruses Alive? Replication...") rather than substantive paragraphs, genuinely too thin for a tutor to answer from even though they're on-topic. A real chunking-quality gap on this one resource, not a harness defect.

Judges every metric with the full model, not the fast classifier model Decision 030 moved live classification to: this harness runs offline with no user waiting, so that latency/cost tradeoff doesn't apply, and a judge should be tuned for reliability the same way Decision 031 kept correctness classification on the full model.

Scoped deliberately to single-turn, direct-answer-eligible cases only, named plainly in the report itself: guided-discovery follow-ups and the escalated strategies (explain, confirm_*) don't produce one single "the answer" to hold up against RAGAS's criteria.

## Impact

* New package `backend/app/rag_eval/` (`context_precision.py`, `context_recall.py`, `faithfulness.py`, `answer_relevancy.py`, `models.py`) -- named distinctly from the pre-existing, unrelated `backend/app/evaluation/` package (the live guardian-dashboard/notifications feature), not placed inside it.
* New `backend/scripts/evaluation/golden_set.py`: 18 cases, one per real ingested `concepts.slug` (6 Eureka Math Grade 6 modules, 12 CK-12 Life Science Grade 6 concepts, confirmed live against the database before writing them), plus 4 deliberately out-of-corpus fallback probes.
* New `backend/scripts/run_evaluation.py` (`python -m scripts.run_evaluation`), following `ingest_content.py`'s existing script conventions. Costs real Anthropic + OpenAI API usage per run.
* New `backend/tests/test_evaluation.py` (14 tests, pure metrics math against hand-written `FakeLLMClient`/`FakeEmbeddingClient` stubs, no network/DB) -- full suite now 89 tests, all passing.
* First real run: 18/18 answerable cases retrieved evidence except one genuine chunking-quality miss (`virus-vs-bacteria`, named above); aggregate scores on the other 17 -- context precision 0.49, context recall 0.94, faithfulness 0.99, answer relevancy 0.71; all 4 fallback probes correctly declined to answer. Full results in `docs/evaluation-report.md` and `backend/scripts/evaluation/results.json`, both committed as the actual deliverable, not just the capability to produce one.

---

# Decision 033

**Date:** 2026-10-06

## Decision

A question that ends low-confidence even after the retrieval retry (Decision 026) is no longer always flatly refused. A new classification step (`classify_answerable_generally`, `app/tutoring/general_knowledge.py`) separates "a real concept for this subject and grade that the ingested curriculum text just doesn't cover" from "actually unrelated to the subject, nonsensical, or not a real concept." The former now gets a clearly-labeled, honest general-knowledge explanation (`generate_general_knowledge_response`, `app/tutoring/generation.py`); the latter still gets the plain refusal.

## Reason

Reported directly: a student focused on "Multi-Digit Decimal Operations" asked "what is a decimal" and got the generic low-confidence fallback. Investigated live before assuming it was a scoping bug: at every retrieval scope (the selected topic, its whole concept, the entire math subject corpus) every retrieved candidate was decimal *operations* content, and the LLM relevance judge (Decision 016) correctly rejected all of it as unable to answer "what is a decimal" -- confirmed by running the production relevance check directly against all 15 candidates, every one `False`. This wasn't a bug: Eureka Math Grade 6 assumes decimals were already defined in an earlier grade and jumps straight to computing with them. The corpus genuinely doesn't have the content.

The explicit ask was for the app to recognize this as a real concept and explain it anyway. That's a real tension with Principle 6 ("Retrieval Before Generation" -- prioritise factual grounding over fluent but unsupported responses) and with the generation prompt's own instruction to never invent beyond the evidence. The resolution kept the principle rather than quietly dropping it: add a second response mode that's honest about not being grounded, instead of either (a) silently generating from the model's general knowledge as if it came from the course, or (b) continuing to refuse a question that deserves a real answer. The disclosure is sent as a deterministic prefix (`GENERAL_KNOWLEDGE_ACKNOWLEDGMENT`), not left to the model to remember -- the same "prompted but not guaranteed" reasoning Decision 019's `ASSIGNMENT_ACKNOWLEDGMENT` already established for the assignment-detection disclosure.

This doesn't reopen Decision 028's "no silent drift" rule (a topic-focused question finding nothing in its scope should be told that plainly, not silently answered from a different topic's content): that rule was about a response falsely appearing grounded in the wrong material. This path never claims any grounding at all, with or without a topic focused.

The new classification call is skipped outright when `safety_category == "sensitive_topic"` -- verified live with a puberty-adjacent question under an unrelated subject (forcing band low): `can_answer_generally` came back `False` without the extra call running, and the router's existing `SENSITIVE_NO_EVIDENCE_MESSAGE` branch is checked first regardless, so a sensitive topic always keeps its own redirect to a trusted adult.

## Impact

* New `app/tutoring/general_knowledge.py`: `classify_answerable_generally(question, subject, grade_band, llm)`, using `classifier_llm` (Haiku, matching the other three narrow classification calls, Decision 030) -- only called on the terminal low-confidence path, so it costs nothing on the normal high-confidence path.
* `graph.py`: new node `classify_general_knowledge`, wired in place of `_route_after_relevance_check`'s old final `return END`; new `TutoringState` field `can_answer_generally`.
* `generation.py`: new `GENERAL_KNOWLEDGE_PROMPT`, `GENERAL_KNOWLEDGE_ACKNOWLEDGMENT`, and `generate_general_knowledge_response(question, history, *, subject, grade_band, llm)`.
* `router.py`'s `band == "low"` branch now checks three cases in order: `sensitive_topic` keeps its dedicated redirect; `can_answer_generally` streams the new honest explanation and records `trace_strategy = "general_knowledge"` in `decision_traces` (free-text column, no migration needed); everything else keeps the flat refusal. That refusal message (`NO_EVIDENCE_MESSAGE`) was also fixed while touching this code -- it was a stale hardcoded list naming only 6 of the 18 real ingested concepts; simplified to not enumerate specific topics at all, so it can't drift out of date again.
* New `backend/tests/test_general_knowledge.py`; full suite now 91 tests, all passing.
* Verified live: the exact reported case now streams a real, accurate, disclosed explanation instead of refusing; genuinely off-subject questions ("who won the super bowl", "what is the capital of France") still decline; a sensitive-but-uncovered question still gets the trusted-adult redirect. One of the eval harness's (Decision 032) four `expect_fallback` golden-set probes ("What is the Pythagorean theorem and how do you use it?") now correctly flips from declining to explaining -- expected, since it's genuine in-subject prerequisite content, not a regression in the harness itself.

---

# Decision 034

**Date:** 2026-10-07

## Decision

A parent can now link directly to their own child's account, no teacher or class code involved, and a stubbed `subscription_status` field gates a free-tier daily question cap -- the premium side of the hybrid go-to-market model discussed alongside the business-strategy artifact. A public, unauthenticated waitlist (email + "parent" or "teacher" interest) ships alongside it, independent of everything else.

## Reason

Driven directly by the GTM discussion: free, teacher-led distribution plus paid parent premium (the Prodigy Math pattern) was identified as the strongest path to a real outcome in this category, and the growth-strategy artifact claimed the schema already anticipated this. That claim turned out to be literally true and not just aspirational: `profiles.role`'s check constraint already allowed `'guardian'` (`20260824000000_initial_schema.sql:20`) and `guardian_links` was already fully link-type-agnostic in every query that reads it (`app/evaluation/guardians.py` -- confirmed via code reading, not assumption, that `is_active_guardian_of`, `_list_students_for_guardian`, and `list_notifications_for_guardian` never check the guardian's role). Nobody had ever written the code path that creates a `guardian` profile. This closes exactly that gap, the mirror image of Decision 024's class-code mechanism rather than a new design: a student's profile carries a `student_link_code` the same way a teacher's carries a `class_code`; a parent redeems one at signup the same way a student redeems a class code. No transactional email infrastructure needed, the same reason Decision 024 avoided it originally.

Scoped deliberately per explicit direction: the premium gate is a daily question cap (new infrastructure, not an existing one repurposed), `subscription_status` is a stubbed DB column flipped by `scripts/set_subscription_status.py` rather than real Stripe integration (that needs a real Stripe account, a decision left for later, not blocking this), and the waitlist ships now because it's independent and immediately useful for recruiting the real classroom pilot the roadmap already calls for.

## Impact

* Migration `20261007000000_parent_accounts_and_waitlist.sql`: `profiles` gains `student_link_code` (unique, `(role = 'student') = (student_link_code is not null)` check, same invariant pattern as `class_code`) and `subscription_status` (`free`/`premium`, default `free`); new `waitlist_signups` table, RLS enabled with no policies since every write goes through the backend's own connection, never a client-side call.
* `app/identity/profiles.py`: `_generate_class_code` generalized to `_generate_short_code`, now generating both `class_code` (teacher) and `student_link_code` (student) with the same retry-on-`UniqueViolation` loop; new `get_student_id_by_link_code`; `create_profile` gained a `guardian` branch, the mirror image of the existing student/`teacher_id` branch with `guardian_id`/`student_id` swapped in the resulting `guardian_links` row.
* `app/tutoring/conversations.py` gained `count_messages_today`; `app/tutoring/router.py`'s `/tutor/ask` short-circuits before running the tutoring graph at all (no wasted LLM cost) when a non-premium student has hit `FREE_DAILY_QUESTION_LIMIT` (10) for the day.
* New `app/waitlist.py` (`POST /waitlist`, idempotent on email) -- the only unauthenticated, write-accepting endpoint in the backend, deliberately.
* Frontend: signup's role toggle gained "Parent" (value `guardian`); the teacher dashboard route (`/teacher`) is now shared by both roles via a `viewerRole` prop on `TeacherClient`, swapping "Your class" for "Your child"/"Your children", hiding the class-code badge, and changing the empty-state copy -- no new route, since `guardian_links` and every `/guardian/*` query already treat both link types identically. `home/home-client.tsx` shows a student their own `student_link_code` to share. New `components/waitlist-form.tsx` on the public landing page.
* `backend/tests/test_class_codes.py` extended with the mirror-image guardian/link-code validation cases; full suite now 96 tests, all passing. Frontend: `tsc --noEmit` clean, `eslint` clean (no new errors).
* Verified live end to end via direct API calls (disposable test users): teacher → student (class code) → parent (student's link code) produced the correct `guardian_links` row in the correct direction; a bad link code 400s cleanly; the existing `/guardian/roster` endpoint worked for the parent with zero backend changes, confirming the link-type-agnostic claim; the daily cap correctly triggered on the 10th question and lifted after `set_subscription_status.py premium`; the waitlist endpoint was idempotent on a duplicate email. Browser-level verification of the signup form itself was partial: the waitlist form was confirmed working end to end in a real browser, and the new three-way role toggle was confirmed rendering correctly by screenshot, but the full student/parent signup-through-dashboard click path hit Supabase's shared email-rate-limit (the same pre-existing constraint already documented earlier in this project) before it could be screenshotted -- the underlying code path is identical to what was already verified via direct API calls, just reached through the UI instead.

---

# Decision 035

**Date:** 2026-10-07

## Decision

A third answer tier exists between Decision 033's two: a question that isn't chunk-grounded but is genuinely about a topic this specific course teaches (not a different, earlier-grade prerequisite) now gets a full-depth, guided-discovery-style answer with no disclosure. "What is a decimal" under a course that teaches decimal operations, or "why do we need decimals when we have ratios" when both are real topics in the course, land here; "what is the Pythagorean theorem" under a Grade 6 course that never teaches it still lands on Decision 033's disclosed prerequisite path.

## Reason

Reported directly against the exact Decision 033 fallback: a follow-up question comparing decimals and ratios (both real topics in the course) still got treated as if it were stepping outside the curriculum, disclosure and all. Discussed directly rather than patched per-question: the real distinction Decision 033 was missing wasn't "grounded vs. not," it was "genuinely part of this course's own topics vs. genuinely outside them" -- a question can fail chunk-level grounding (no single retrieved passage supports it) while still being squarely inside the course (the topic itself is covered, just not that specific angle on it). Explicitly scoped during discussion: guided discovery itself -- the anchor+question shape, assignment detection, the escalation state machine -- had to keep working identically across all three tiers; only the scope gate was ever up for change, not the teaching style.

The gate is checked against the actual list of topic names this subject/grade covers (`get_concept_names`, new in `app/retrieval/store.py`), not a generic "is this a legitimate concept" judgment -- that's deliberately still what Decision 033's original classifier asks, now second in line, for the case where a question really is outside this course's own topics but still worth explaining honestly. When a question matches a real topic directly, the second, more generic classifier call is skipped entirely, since that's now the more common case, not the exception.

`generate_grounded_response` couldn't be reused for the new tier even with an empty evidence list: it structurally renders a `"Curriculum evidence:\n\n..."` block into every prompt, and its own instructions explicitly tell the model to stay limited to that evidence -- passing it nothing would have actively suppressed the full-depth answer this tier exists to give. A sibling function with the same two-part prompt shape, not a parameterization of the grounded one, was the only way to keep the teaching style identical without fighting the existing prompt's own constraints.

## Impact

* `app/retrieval/store.py`: new `get_concept_names(pool, subject_slug, grade_band)` -- a bare `concepts`/`subjects` query, deliberately not reusing `get_topic_progress`'s join (`app/tutoring/progress.py`), which exists to compute per-student mastery through `document_chunks`/`decision_traces` and would cost far more than this needs.
* `app/tutoring/general_knowledge.py`: new `classify_topic_in_scope(question, topics, subject, grade_band, llm)` + `TopicScopeJudgment`, checked first; `classify_answerable_generally` unchanged, now the second check.
* `app/tutoring/graph.py`: `_classify_general_knowledge_node` extended (not replaced) to check topic-in-scope before the original prerequisite question; new `TutoringState` field `topic_in_scope`.
* `app/tutoring/generation.py`: new `IN_SCOPE_PROMPT` + `generate_in_scope_response` -- same anchor+question shape, same `ASSIGNMENT_NOTICE`/`ASSIGNMENT_ACKNOWLEDGMENT` mechanism as the grounded path, no disclosure prefix.
* `app/tutoring/router.py`'s `band == "low"` branch gained a fourth case, checked in order: `sensitive_topic` (unchanged) -> `topic_in_scope` (new) -> `can_answer_generally` (Decision 033, unchanged) -> flat refusal (unchanged). Records `trace_strategy = "guiding_in_scope"` (free-text column, no migration).
* New tests in `backend/tests/test_general_knowledge.py` for `classify_topic_in_scope`; full suite now 98 tests, all passing.
* Verified live against the exact reported case: "what is a decimal" and the decimals-vs-ratios follow-up both now stream full-depth, guided-discovery-style answers (anchor + one genuine question, no disclosure); "what is the Pythagorean theorem" still correctly falls through to the disclosed path; a pasted-assignment-style question landing on this tier still gets the assignment acknowledgment and withholds the final answer, confirming guided discovery and academic integrity hold across all three tiers as required.

---

# Decision 036

**Date:** 2026-10-09

## Decision

Push-to-talk voice mode: a mic button lets a student speak a question instead of typing it (transcribed into the same editable input box, nothing sent automatically), and a "Voice on/off" toggle has the tutor's replies read aloud when on. Built entirely with browser-native Web Speech APIs (`SpeechRecognition`, `SpeechSynthesis`) -- no backend change, no new paid vendor, no new ongoing cost.

## Reason

Requested explicitly as the cheap, real first version of voice conversation, not ChatGPT's full real-time duplex Advanced Voice Mode -- that's a materially different, much larger system (streaming audio, interruption handling) and a separate future decision. Confirmed before building that this was fully achievable with built-in browser APIs alone: `SpeechSynthesis` ships fully typed in this project's TypeScript already; `SpeechRecognition` doesn't exist in the bundled `lib.dom.d.ts` at all, so a small hand-written ambient declaration was added rather than pulling in `@types/dom-speech-recognition` for the handful of members actually used.

The transcript lands in the same `question` state the typed textarea already uses, not a separate send-on-speak path -- preserves the same "review before it's sent" property the file-attachment transcription preview already has, for the same reason: speech-to-text, like OCR, is imperfect, and a student should see and be able to fix a misheard word before it reaches the tutor.

Read-aloud is a persistent mode (a toggle next to the existing FOCUSED/GUIDING header badges), not a per-message speaker icon -- it's meant to feel like an actual voice conversation setting, not an accessibility button bolted onto each bubble. Defaults off: auto-speaking a reply the student never asked to hear would be a bad surprise.

`SpeechRecognition` has materially worse browser support than `SpeechSynthesis` (inconsistent or absent in Safari/Firefox desktop) -- the mic button simply doesn't render when neither `window.SpeechRecognition` nor `window.webkitSpeechRecognition` exists, checked via a `useEffect` after mount (not inline, since `window` doesn't exist during Next.js's server render and checking inline would cause a hydration mismatch).

## Impact

* New `frontend/src/types/speech-recognition.d.ts`: a minimal ambient `SpeechRecognition` interface typing only what's used (`start`, `stop`, `onresult`, `onerror`, `onend`, `continuous`, `interimResults`, `lang`).
* `frontend/src/app/chat/chat-client.tsx`: new state (`voiceMode`, `listening`, `voiceError`, `voiceSupport`), `toggleListening()` wiring a `SpeechRecognition` instance to the existing `setQuestion`, and a post-stream hook in `handleSubmit` that speaks the completed reply via `speechSynthesis.speak(...)` when voice mode is on. New mic button in the existing input row (matches the "Attach file" button styling) and a voice-mode toggle in the header (matches the FOCUSED/GUIDING badge styling), both gated on feature detection.
* No backend files touched at all.
* `tsc --noEmit` and `eslint` clean. Verified live in a real browser (logged in as the premium test student): both buttons render correctly, the voice toggle switches state and styling correctly, and normal text-based chat is unaffected (no console errors, no regressions).
* **Known verification gap, stated plainly**: the actual speech-to-text and text-to-speech round trip (does speaking really fill the box correctly, does a reply actually get read aloud) needs a real microphone and speakers in a real browser -- genuinely not something automatable in this headless environment (fake-media-stream mocking satisfies `getUserMedia` but not Chrome's actual speech-recognition backend). That half of verification is still pending a manual check.

---

# Decision 036 (revised)

**Date:** 2026-10-09

## Decision

Voice mode now auto-submits when the student stops speaking, instead of filling the input box and waiting for a manual send.

## Reason

Reported directly after the first version shipped: clicking the mic and speaking "did nothing" from the student's point of view -- the original design (fill the box, require a manual send, mirroring the file-attachment transcription-review pattern) gave no feedback that anything had happened until the student looked down at the box themselves. Asked directly and confirmed: auto-submit on release is the wanted behavior, accepting the tradeoff that a misheard word now goes straight to the tutor rather than getting a review step first -- a real tradeoff, stated plainly, not silently dropped.

Implementing this surfaced a real correctness issue worth naming: `recognition.onend`'s handler is set up once, when listening starts, so it can't safely read the `question` React state when it fires moments later -- a `setState` from `onresult` isn't guaranteed to be visible yet. Fixed by tracking the transcript in a plain local variable inside the same closure and passing it directly into a new shared `submitQuestion(raw)` helper (extracted from the form's `handleSubmit`, which now just reads `question` state and forwards it) -- avoids the stale-read entirely rather than working around it.

## Impact

* `frontend/src/app/chat/chat-client.tsx`: `handleSubmit` split into a thin form handler plus `submitQuestion(raw: string)`, shared by both the typed-submit path and voice; `toggleListening`'s `onend` now calls `submitQuestion(finalTranscript)` when there's real transcribed text, using a closure-local variable rather than reading back out of state.
* Verified live, genuinely end to end, not just UI rendering: macOS's own text-to-speech synthesized a real spoken question into a WAV file, fed to Chrome as a fake microphone via `--use-file-for-fake-audio-capture`, so Chrome's actual cloud speech-recognition service did real transcription (not a mock). Clicking "Speak" correctly transcribed "what is a ratio," auto-submitted with no further click, and the real backend returned a correct, grounded, guided-discovery answer -- the full pipeline confirmed working, not assumed.

---

# Decision 036 (hardened)

**Date:** 2026-10-09

## Decision

`toggleListening` now defensively cleans up any stale `SpeechRecognition` instance before starting a new one, and wraps `recognition.start()` in a try/catch -- either failure now surfaces a visible error message instead of leaving the mic button stuck on "Listening..." with no feedback at all.

## Reason

Reported directly: clicking the mic, speaking, and releasing produced no visible result. `recognition.start()` throws synchronously (`InvalidStateError`) if a recognizer is already active -- and since `listening` was set to `true` *before* calling `.start()`, a throw there left the button showing "Listening..." indefinitely with no error surfaced and no way to recover except a page reload. Couldn't fully rule out this being the actual cause versus testing against a not-yet-deployed build (the same deploy-timing confusion hit more than once already this session) -- fixed the real gap regardless, since a silent failure mode is worth closing either way.

## Impact

* `frontend/src/app/chat/chat-client.tsx`'s `toggleListening`: stops any existing `recognitionRef.current` (wrapped in try/catch, since stopping an already-stopped or never-started recognizer can itself throw) before creating a new one; `recognition.start()` wrapped in try/catch, reverting `listening` to `false` and setting a visible `voiceError` message on failure instead of leaving the UI stuck.
* Verified live: re-ran the same real-speech-to-real-answer end-to-end test (synthesized audio fed to Chrome as a fake microphone) to confirm normal operation is unaffected, plus a deliberate rapid-double-click stress test targeting the exact stale-instance scenario this fix addresses -- no stuck state, no silent failure, the mic button correctly returned to its idle state every time.

---

# Decision 036 (no-speech feedback)

**Date:** 2026-10-09

## Decision

When voice recognition ends with no speech captured, the student now sees "Didn't catch anything. Try again, a little closer to the mic." instead of the mic button silently reverting with no feedback at all.

## Reason

Reported directly, with a screenshot: speaking and releasing produced nothing, and attempting to submit the empty box just surfaced the browser's own generic "Please fill out this field" validation -- not a message this app controls, and not helpful. Root cause: some browsers end `SpeechRecognition` on silence without ever firing `onerror`, so a zero-transcript result and a real working-but-nothing-heard mic looked identical -- both were silent. The screenshot's visible "super" message turned out to be leftover from this session's own automated testing (local dev and production share one database, confirmed earlier this project), not from the student's own attempt -- cleared directly from the database, unrelated to this code fix.

## Impact

* `frontend/src/app/chat/chat-client.tsx`'s `toggleListening`: `onend` now distinguishes "got a transcript, submit it" from "got nothing, say so" instead of silently doing nothing in the latter case.
* Verified live: fed two seconds of genuine silence to Chrome's real speech-recognition pipeline (via `--use-file-for-fake-audio-capture`, not a mock) and confirmed the new message appears and the mic button cleanly resets, instead of silence.
* Cleaned up the shared test account's conversation history in the database (two conversations, both from this session's own prior automated tests) so the next live test starts from a genuinely clean slate.
