import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Connection pool: min 1, max 10 connections
_connection_pool: pool.ThreadedConnectionPool | None = None


def get_pool() -> pool.ThreadedConnectionPool:
    """Lazily initialize and return the connection pool."""
    global _connection_pool
    if _connection_pool is None or _connection_pool.closed:
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=settings.DATABASE_URL,
            cursor_factory=RealDictCursor,
        )
        logger.info("Database connection pool created")
    return _connection_pool


@contextmanager
def get_db_connection(autocommit: bool = False):
    """Context manager for database connections using the pool.

    Args:
        autocommit: If True, commits after yield. Default False (caller manages commits).
    """
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
        if autocommit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        p.putconn(conn)


def close_pool():
    """Close the connection pool (call on shutdown)."""
    global _connection_pool
    if _connection_pool and not _connection_pool.closed:
        _connection_pool.closeall()
        logger.info("Database connection pool closed")
        _connection_pool = None


def check_database_health() -> bool:
    """Check database connectivity"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
