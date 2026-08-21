"""
Thin interfaces for external AI providers, each with exactly one concrete
adapter for now: Anthropic Claude for generation and classification,
OpenAI text-embedding-3 for embeddings.

Every call site in the tutoring and retrieval modules depends on the
interfaces in this package, never on a vendor SDK directly, so adding a
second provider later is a new adapter class, not a refactor. See
architecture §17 and Decision 014.
"""
