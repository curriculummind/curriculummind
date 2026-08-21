"""
Decision trace recording for internal debugging and capstone
demonstration.

Persists the tutoring pipeline's own state (intent, retrieval candidates,
selected strategy, provider/latency per stage) as a byproduct of the
pipeline run. Admin-only access — never exposed to students or guardians.
See architecture §23.
"""
