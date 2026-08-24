"""
Shared async Postgres connection pool, used by every module that reads
or writes the database directly (retrieval's vector search bypasses an
ORM deliberately, since pgvector's distance operators are plain SQL).
"""

from functools import lru_cache

from psycopg_pool import AsyncConnectionPool

from app.config import get_settings


@lru_cache
def get_pool() -> AsyncConnectionPool:
    """Return the process-wide connection pool, created once and cached."""
    settings = get_settings()
    return AsyncConnectionPool(conninfo=settings.database_url, open=False)
