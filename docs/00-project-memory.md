# CurriculumMind Project Memory

## Project Identity

**Project:** CurriculumMind
**Tagline:** Adaptive Learning Intelligence for Modern Education

## Current MVP Scope

**Target grades:** 6–12

**Initial subjects:**

* Computer Science
* Science

**Current curriculum direction:**

* US curriculum-aligned resources for the MVP
* Architecture must support additional curricula later
* Curriculum is modeled as a curriculum-agnostic Concept taxonomy, with CurriculumFramework and Standard attached as a mapping layer rather than a single flat "Curriculum" entity — see Decision 008

## Initial Build Target (Capstone Phase)

The first working slice, ahead of the full 6–12 / Computer Science + Science MVP above, is:

**Grade:** 6 only
**Subjects:** Mathematics and Science
**Content sources:** EngageNY / Eureka Math (Grade 6 math), CK-12 (Grade 6 science) — both free, open-license, non-commercial-use content, suitable for capstone/academic use
**Standards mapping:** Common Core (math) and NGSS (science) standards documents, used as the Standard/CurriculumFramework layer, not as retrievable content

⚠️ **Pre-commercial-launch requirement:** CK-12 and EngageNY content is licensed for non-commercial/educational use only. Before curriculummind.com charges money or operates as a funded startup, this content must be replaced or re-licensed — see Decision 013.

## Future Expansion

The architecture should support future expansion to:

* K–5
* Additional subjects
* Multiple curricula
* International education systems
* School-specific curriculum configurations

## AI Strategy

CurriculumMind is **not** a foundation-model training project.

The MVP will use existing hosted language models and build the system intelligence through:

* Retrieval-Augmented Generation
* Agentic workflows
* Curriculum retrieval
* Student context
* Pedagogical routing
* Assignment detection
* Evaluation and learning analytics

The architecture should avoid hard dependency on a single LLM provider.

## Core Product Principle

CurriculumMind should teach students rather than simply provide answers.

The system should:

* understand student intent,
* retrieve verified curriculum material,
* choose an appropriate tutoring strategy,
* adapt to grade level,
* detect assignment-like requests,
* provide guided discovery when appropriate,
* and measure learning signals over time.

## Current Technical Direction

**Frontend:** Next.js + TypeScript
**UI:** Tailwind CSS + shadcn/ui
**Authentication:** Supabase Auth
**Database:** Supabase PostgreSQL
**Vector search:** pgvector
**AI backend:** Python + FastAPI
**Backend architecture:** Modular monolith — one FastAPI service with strong internal module boundaries (`tutoring/`, `retrieval/`, `curriculum/`, `identity/`, `evaluation/`, `observability/`), not microservices — see Decision 011
**Agent orchestration:** LangGraph, scoped to a deterministic pipeline graph (fixed node sequence with two conditional branches) — not an autonomous tool-calling agent — see Decision 006
**Version control:** Git + GitHub
**Primary coding agent:** Claude Code
**Primary IDE:** VS Code

**Production domain:** curriculummind.com
**Frontend hosting:** Vercel
**Backend hosting:** Render (FastAPI service + background worker)
**Error tracking:** Sentry (frontend + backend)

## Repository Philosophy

Git is the source of truth for important project decisions.

Important product, architecture, AI, and implementation decisions should be written into repository documentation rather than relying only on conversation history.

## Development Philosophy

Build incrementally.

Prefer:

* working vertical slices,
* clean architecture,
* real persistence,
* real RAG,
* real classification and routing,
* small Git commits,
* explicit scope control,
* maintainable code.

Avoid unnecessary complexity and premature features.
