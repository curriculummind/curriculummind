"""
Asynchronous evaluation: faithfulness and relevance scoring, learning
signal aggregation, guardian summary materialization, and alerts.

Runs entirely in the background worker after a message has already been
persisted and streamed to the student — never in the synchronous request
path. See architecture §21-§22.
"""
