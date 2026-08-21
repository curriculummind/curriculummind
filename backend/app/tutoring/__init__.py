"""
Tutoring pipeline: safety checks, intent and assignment classification,
strategy selection, and response generation.

Implements the deterministic request lifecycle from architecture §8-§11 —
a fixed node sequence with two conditional branches (retrieval-confidence
retry, assignment-detected override), not an autonomous tool-calling agent.
"""
