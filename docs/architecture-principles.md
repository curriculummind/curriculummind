# CurriculumMind Architecture Principles

## Purpose

This document defines the architectural principles that govern the design, implementation, and long-term evolution of CurriculumMind.

These principles serve as the **constitutional rules** of the project.

Every architecture document, implementation decision, database design, AI workflow, API, and future feature must remain consistent with these principles.

If a proposed change violates one or more principles, the architecture should be reconsidered before implementation.

---

# Scope

These principles apply to:

* backend architecture
* AI architecture
* tutoring engine
* retrieval system
* curriculum management
* database design
* APIs
* frontend architecture
* infrastructure
* future feature expansion

---

# Principle 1 — Education Before Technology

## Statement

CurriculumMind is an educational platform before it is an AI platform.

Technology exists to improve learning rather than demonstrate AI capability.

Every engineering decision should increase educational value.

## Rationale

The primary objective of CurriculumMind is to help students become independent learners.

The system should optimize for learning rather than answer generation.

## Origin

✅ Directly aligned with the capstone proposal.

---

# Principle 2 — Backend Before Frontend

## Statement

The backend defines the product.

The frontend presents the product.

Core educational behaviour must be designed before UI implementation.

Examples include:

* tutoring workflow
* curriculum retrieval
* pedagogical routing
* student modelling
* evaluation

UI decisions must never force architectural compromises.

## Origin

🔄 Architectural refinement.

---

# Principle 3 — Domain Before Implementation

## Statement

The educational domain should be modelled before implementation details.

The system should first understand concepts such as:

* Student
* Parent
* Curriculum
* Subject
* Concept
* Learning Session
* Conversation
* Assignment
* Hint
* Evaluation

Only after the domain is clearly defined should the implementation be designed.

This includes:

* databases
* APIs
* LangGraph
* prompts
* UI

## Origin

💡 New architectural recommendation based on Domain-Driven Design.

---

# Principle 4 — Stable Tutoring Engine

## Statement

The tutoring engine is the heart of CurriculumMind.

Everything else exists to support it.

Future additions should extend the tutoring engine without redesigning it.

Examples:

* new grades
* new subjects
* new curricula
* additional AI providers
* new evaluation metrics

should require extension rather than architectural restructuring.

## Origin

✅ Derived from the proposal's emphasis on a stateful tutoring agent that decides how to teach before generating responses.

---

# Principle 5 — Pedagogical Decision Before Response

## Statement

The system should make educational decisions before generating responses.

The tutoring pipeline should determine:

1. student context
2. intent
3. assignment likelihood
4. curriculum evidence
5. tutoring mode
6. learning strategy

Only then should the language model generate a response.

Response generation is the final stage of the tutoring process.

## Origin

✅ Directly derived from the proposed tutoring workflow.

---

# Principle 6 — Retrieval Before Generation

## Statement

Curriculum-grounded retrieval must precede educational generation whenever curriculum knowledge is required.

Language models should reason over retrieved educational evidence rather than relying solely on parametric knowledge.

The architecture should prioritise factual grounding over fluent but unsupported responses.

## Origin

✅ Directly aligned with the proposed RAG pipeline.

---

# Principle 7 — Configuration Over Hard Coding

## Statement

Educational behaviour should be configurable.

Examples include:

* grade bands
* curricula
* tutoring modes
* evaluation thresholds
* retrieval filters
* pedagogical policies

Adding educational capability should primarily involve configuration and content rather than rewriting code.

## Origin

🔄 Architectural refinement.

---

# Principle 8 — Curriculum Independence

## Statement

The tutoring engine must remain independent of any specific curriculum.

Curriculum should exist as a configurable layer.

Future additions should include:

* Common Core
* NGSS
* CBSE
* ICSE
* State Boards
* International curricula

without changing the tutoring engine.

## Origin

🔄 Architectural refinement of the proposal's curriculum-grounding approach.

---

# Principle 9 — Subject Independence

## Statement

Subjects should be treated as plug-in educational domains.

The MVP supports:

* Computer Science
* Science

Future additions may include:

* Mathematics
* English
* History
* Geography
* Economics

Adding a subject should require:

* curriculum content
* subject configuration
* pedagogical adjustments

rather than redesigning the backend.

## Origin

💡 New architectural recommendation.

---

# Principle 10 — AI Provider Independence

## Statement

CurriculumMind should never depend on a single language model provider.

The tutoring engine should remain stable while AI providers may evolve.

Examples include:

* Anthropic
* OpenAI
* Gemini
* future providers

Changing providers should not require architectural redesign.

## Origin

💡 New architectural recommendation.

---

# Principle 11 — Observability

## Statement

Every educational decision should be observable.

The architecture should expose:

* retrieval traces
* tutoring decisions
* assignment detection
* tool execution
* evaluation metrics
* learning signals

without requiring manual debugging.

## Origin

🔄 Architectural refinement of the proposal's logging and evaluation pipeline.

---

# Principle 12 — Continuous Educational Improvement

## Statement

CurriculumMind should continuously evaluate its educational effectiveness.

Evaluation should measure:

* retrieval quality
* answer grounding
* learning progress
* repeated confusion
* hint dependency
* educational outcomes

Future improvements should be driven by evidence rather than intuition.

## Origin

✅ Directly aligned with the proposal's continuous improvement loop.

---

# Principle 13 — Documentation Is Architecture

## Statement

Repository documentation forms part of the system architecture.

Important decisions should be documented.

Repository documentation—not AI conversations—represents the long-term memory of CurriculumMind.

## Origin

💡 Repository governance recommendation.

---

# Principle 14 — Incremental Vertical Slices

## Statement

Features should be implemented as complete vertical slices.

Each slice should:

* function correctly
* be documented
* be tested
* be committed independently

Large unfinished implementations should be avoided.

## Origin

🔄 Engineering methodology refinement.

---

# Principle 15 — Extensibility Without Redesign

## Statement

Future expansion should require extension rather than restructuring.

Future capabilities include:

* K–5 education
* additional subjects
* multiple curricula
* multiple AI providers
* richer evaluation systems

The tutoring engine should remain stable while surrounding components evolve.

## Origin

🔄 Long-term architectural refinement.

---

# Principle 16 — Simplicity With Explicit Extension Points

## Statement

The MVP should remain intentionally focused.

Complexity should only be introduced when it creates long-term architectural value.

Every major subsystem should expose clear extension points while avoiding premature implementation.

## Origin

💡 Software architecture recommendation.

---

# Definition of Architectural Success

The CurriculumMind architecture is considered successful if future expansion primarily requires:

* new curriculum content,
* new pedagogical policies,
* additional configuration,
* adapters,
* plugins,

rather than redesigning the backend.

---

# Architectural Review Checklist

Before accepting any major architectural change, ask:

* Does this improve learning?
* Does this preserve backend stability?
* Does this preserve tutoring engine independence?
* Does this support future curricula?
* Does this support future subjects?
* Does this minimise hard-coded assumptions?
* Does this follow the documented architecture?
* Does this preserve long-term extensibility?

If the answer to any question is **No**, the proposed architecture should be reconsidered before implementation.
