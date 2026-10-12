import os
import json
from contextlib import contextmanager

_pool = None


def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    try:
        import psycopg2
        from psycopg2 import pool as pg_pool
        _pool = pg_pool.SimpleConnectionPool(1, 5, dsn=url)
        return _pool
    except Exception:
        return None


@contextmanager
def get_conn():
    pool = _get_pool()
    if pool is None:
        yield None
        return
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def init_schema():
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_conn() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_pipelines (
                    id           SERIAL PRIMARY KEY,
                    name         TEXT NOT NULL,
                    recipe       JSONB NOT NULL,
                    dataset_meta JSONB,
                    created_at   TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_pipelines_created
                    ON saved_pipelines (created_at DESC);
            """)
        return True


def save_pipeline(name: str, recipe: dict, dataset_meta: dict = None) -> int:
    with get_conn() as conn:
        if conn is None:
            raise RuntimeError("No DATABASE_URL configured.")
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO saved_pipelines (name, recipe, dataset_meta) VALUES (%s, %s, %s) RETURNING id",
                (name, json.dumps(recipe), json.dumps(dataset_meta or {})),
            )
            return cur.fetchone()[0]


def list_pipelines(limit: int = 50):
    with get_conn() as conn:
        if conn is None:
            return []
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, dataset_meta, created_at FROM saved_pipelines ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return [
                {"id": r[0], "name": r[1], "meta": r[2], "created_at": r[3].isoformat()}
                for r in cur.fetchall()
            ]


def get_pipeline(pid: int):
    with get_conn() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, recipe FROM saved_pipelines WHERE id = %s", (pid,))
            row = cur.fetchone()
            return {"id": row[0], "name": row[1], "recipe": row[2]} if row else None


def delete_pipeline(pid: int):
    with get_conn() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("DELETE FROM saved_pipelines WHERE id = %s", (pid,))
            return cur.rowcount > 0