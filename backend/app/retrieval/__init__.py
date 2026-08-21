"""
RAG retrieval: query embedding, metadata filtering, similarity ranking,
and confidence gating.

Metadata (subject, grade band, concept, curriculum framework) filters the
candidate set before vector similarity runs, per architecture §15. No
dedicated reranker at MVP — see the decision record in §31.
"""
