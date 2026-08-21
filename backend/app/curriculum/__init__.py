"""
Curriculum domain: subjects, the curriculum-agnostic concept taxonomy,
curriculum frameworks, and standards mapping.

Concept is the stable unit the tutoring engine reasons over. Curriculum
frameworks (e.g. Common Core, NGSS) and standards attach to concepts as a
many-to-many mapping layer rather than owning them, so a new framework is
a data addition, not a schema change. See architecture §13.
"""
