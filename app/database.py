"""PostgreSQL connection pool — single shared pool for all CRUD ops."""
import logging
from contextlib import contextmanager
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

logger = logging.getLogger("formulary_api")

_pool: ThreadedConnectionPool | None = None


def init_pool(minconn: int = 1, maxconn: int = 10):
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(minconn, maxconn, **DB_CONFIG)
        logger.info("DB pool created (%s:%s/%s)", DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["dbname"])
    return _pool


def close_pool():
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("DB pool closed")


@contextmanager
def get_conn():
    """Yield a live connection; auto-rollback + return to pool."""
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT 1")
        conn.rollback()
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        is_dead = conn.closed != 0
        _pool.putconn(conn, close=is_dead)


@contextmanager
def get_cursor(cursor_factory=RealDictCursor):
    """Yield a RealDictCursor inside a managed connection."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            yield cur
        conn.commit()
