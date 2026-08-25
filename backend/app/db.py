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
    return AsyncConnectionPool(
        conninfo=settings.database_url,
        open=False,
        # Supabase's transaction-mode pooler closes idle backend
        # connections server-side. Without this, the client pool hands
        # out a connection it still believes is healthy and the request
        # fails with "server closed the connection unexpectedly" --
        # check_connection validates (and transparently reconnects) on
        # checkout instead of surfacing that as a request failure.
        check=AsyncConnectionPool.check_connection,
        max_idle=120,
        # Supabase's transaction-mode pooler multiplexes many client
        # sessions onto the same underlying server connections. psycopg's
        # automatic server-side statement preparation is tied to that
        # server connection, not our logical session, so a prepared
        # statement from one request can collide with another's --
        # "prepared statement already exists". Disabling autoprepare is
        # the standard fix for psycopg3 behind a transaction-mode pooler.
        kwargs={"prepare_threshold": None},
    )
