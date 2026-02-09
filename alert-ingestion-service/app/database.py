import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from app.config import settings

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(
            settings.DATABASE_URL,
            cursor_factory=RealDictCursor
        )
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

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
