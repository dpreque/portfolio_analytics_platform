# src/db/connection.py
# ---------------------------------------------------------------------------
# PostgreSQL connection layer (psycopg v3 + psycopg_pool).
# ---------------------------------------------------------------------------
# Exposes get_connection() as the single data-access entry point used by every
# service and the seed/build scripts:
#
#     with get_connection() as conn:
#         cur = conn.cursor()
#         cur.execute("SELECT ... WHERE x = %s", (val,))
#         rows = cur.fetchall()        # rows are dict-like (psycopg dict_row)
#
# The context manager commits on clean exit, rolls back on exception, and
# returns the connection to the pool. Callers must NOT commit/rollback/close.
#
# Connection info comes from the environment (single read-point get_conninfo):
#   DATABASE_URL=postgresql://user:pass@host:5432/dbname        (wins if set)
#   or PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD        (localhost defaults)
# The pool opens lazily, so importing this module never needs a live database
# (the app boots; queries fail clearly if PostgreSQL is unreachable).
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator

from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Populate connection env vars from a gitignored repo-root `.env` (real
    environment variables always win). Lets the project point at PostgreSQL
    without exporting vars in every shell. Format: KEY=value per line."""
    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def get_conninfo() -> str:
    """Single read-point for the PostgreSQL connection string (env-driven)."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    dbname = os.environ.get("PGDATABASE", "analytics")
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "postgres")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


_pool: ConnectionPool | None = None
_opened = False


def _get_pool() -> ConnectionPool:
    """Lazily build + open a shared connection pool (dict rows)."""
    global _pool, _opened
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=get_conninfo(),
            min_size=1,
            max_size=int(os.environ.get("DB_POOL_MAX", "10")),
            kwargs={"row_factory": dict_row},
            open=False,
            name="analytics-api",
        )
    if not _opened:
        _pool.open()  # non-blocking; PoolTimeout surfaces on connection() if DB is down
        _opened = True
    return _pool


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Yield a pooled psycopg Connection; commit/rollback/return handled here."""
    pool = _get_pool()
    with pool.connection() as conn:
        yield conn
