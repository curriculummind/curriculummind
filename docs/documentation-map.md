# CurriculumMind Documentation Map

## Purpose

This document defines the documentation architecture for the CurriculumMind repository.

It explains:

* what documentation exists,
* why each document exists,
* who should read it,
* when it should be updated,
* and how the documentation supports both human developers and AI coding agents.

This document should be reviewed before creating new documentation to avoid duplication and maintain a clean architecture.

---

# Documentation Philosophy

Documentation is considered part of the software architecture.

The repository documentation is the long-term memory of the project.

Neither ChatGPT nor Claude Code should be treated as the project's memory.

The Git repository is the authoritative source of truth.

All important architectural, product, AI, and implementation decisions should eventually be reflected in repository documentation.

---

# Documentation Categories

The documentation is organized into four categories.

## 1. Living Documents

Living documents evolve throughout the project.

They represent the current state of the system.

Examples include:

* Project Memory
* Engineering Decisions
* Development Roadmap
* Changelog

These documents will be updated frequently.

---

## 2. Architecture Documents

Architecture documents describe how the system is designed.

They should remain relatively stable.

Changes should occur only after careful architectural discussion.

Examples include:

* Product Strategy
* System Architecture
* Domain Model
* AI Architecture
* RAG Architecture
* Database Design
* API Design

---

## 3. Developer Documentation

Developer documentation explains how to build, run, deploy, and contribute to CurriculumMind.

Examples include:

* README
* Setup Guide
* Deployment Guide
* Coding Standards
* AI Playbook

---

## 4. AI Working Documents

These documents exist specifically to improve collaboration with AI coding assistants.

They describe:

* current sprint,
* implementation priorities,
* repository conventions,
* coding workflow,
* documentation reading order.

These documents are intended for Claude Code and future AI assistants.

---

# Repository Documentation Structure

The project documentation will follow this structure.

## Root

README.md

Public introduction to CurriculumMind.

Audience:

* developers
* recruiters
* professors
* contributors

---

PROJECT_SPEC.md

Master documentation index.

This document points to all other project documentation.

AI assistants should begin here.

---

CHANGELOG.md

Chronological history of major milestones.

---

## docs/

### 00-project-memory.md

Purpose

Current factual state of the project.

Contains:

* MVP scope
* technology stack
* AI strategy
* current implementation status
* project philosophy

Updated whenever the project's current state changes.

---

### 10-decisions.md

Purpose

Architecture Decision Record (ADR) log.

Each decision records:

* decision
* rationale
* consequences
* status

Never delete historical decisions.

---

### 20-product-strategy.md

Purpose

Defines the long-term vision of CurriculumMind.

Contains:

* mission
* educational philosophy
* target users
* competitive positioning
* MVP definition
* future expansion

---

### 30-system-architecture.md

Purpose

Defines the overall backend architecture.

This is the most important technical document in the repository.

Contains:

* system modules
* architectural layers
* service boundaries
* extension strategy
* backend philosophy

Every major implementation decision should remain consistent with this document.

---

### 40-domain-model.md

Purpose

Defines the core business entities.

Examples include:

* Student
* Parent
* Conversation
* Curriculum
* Lesson
* Learning Session
* Assignment
* Retrieval
* Evaluation

This document represents the conceptual model of the platform.

---

### 50-ai-architecture.md

Purpose

Defines the tutoring engine.

Includes:

* LangGraph
* agent state
* orchestration
* tutoring modes
* assignment detection
* student modeling
* prompt strategy

---

### 60-rag-architecture.md

Purpose

Defines the curriculum retrieval system.

Includes:

* ingestion
* chunking
* metadata
* embeddings
* pgvector
* reranking
* grounding

---

### 70-database-design.md

Purpose

Defines the logical database model.

Includes:

* tables
* relationships
* indexes
* security
* row-level security
* migration strategy

---

### 80-api-design.md

Purpose

Defines communication between frontend and backend.

Includes:

* REST endpoints
* request models
* response models
* authentication
* error handling

---

### 90-ui-ux-design.md

Purpose

Defines application screens and user experience.

Contains:

* navigation
* screen hierarchy
* design principles
* accessibility
* interaction patterns

---

### 100-development-roadmap.md

Purpose

Defines implementation order.

Includes:

* milestones
* sprints
* backlog
* priorities

Updated throughout development.

---

### 110-ai-playbook.md

Purpose

Instruction manual for AI coding assistants.

Defines:

* required reading order
* coding standards
* Git workflow
* documentation workflow
* implementation rules
* commit strategy

This document allows Claude Code (and future AI assistants) to work consistently across long development cycles.

---

# Reading Order

New developers should read:

1. README.md
2. PROJECT_SPEC.md
3. 00-project-memory.md
4. 10-decisions.md

AI coding assistants should then continue with:

5. Product Strategy
6. System Architecture
7. Domain Model
8. AI Architecture
9. RAG Architecture
10. Database Design
11. API Design
12. UI Design
13. Development Roadmap
14. AI Playbook

---

# Documentation Principles

Every document should satisfy the following rules:

* Have a single, well-defined responsibility.
* Avoid duplicating information found elsewhere.
* Be understandable without relying on chat history.
* Prefer architecture over implementation details.
* Keep implementation decisions traceable to documented architecture.
* Update documentation when significant architectural decisions change.
* Preserve historical decisions rather than rewriting project history.

The documentation should evolve alongside the software and remain the long-term memory of CurriculumMind.
