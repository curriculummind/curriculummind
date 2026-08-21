"""
Identity domain: student and guardian profiles, guardian-student links,
and authorization boundaries.

Guardians hold no direct read access to Conversation or Message tables —
they read only from the derived summary materialized by evaluation/. See
architecture §19.
"""
