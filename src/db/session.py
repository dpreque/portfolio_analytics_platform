# src/db/session.py
# ---------------------------------------------------------------------------
# Reference DB session layer (SQLite) for FRONT-END DEVELOPMENT ONLY.
# ---------------------------------------------------------------------------
# Mirrors the contract documented for the real ETL backend so service code
# reads identically against either store:
#
#     with get_connection() as conn:
#         cur = conn.cursor()
#         cur.execute("SELECT ... WHERE x = ?", (val,))
#         rows = cur.fetchall()        # rows are dict-like (sqlite3.Row)
#
# The context manager commits on clean exit, rolls back on exception, and
# closes. Callers must NOT call commit/rollback/close themselves.
#
# Porting to the real backend (PostgreSQL + psycopg v3) is mechanical:
#   - swap this module's internals for psycopg's ConnectionPool
#   - change parameter placeholders '?' -> '%s' in the service SQL
#   - rows already arrive dict-like (psycopg dict_row)
# The HTTP/JSON API contract above this layer is unchanged.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

# Repo root is two levels up from this file (src/db/session.py -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB_PATH = _REPO_ROOT / "data" / "reference.db"


def get_db_path() -> Path:
    """Single read-point for the reference DB location (override via env)."""
    return Path(os.environ.get("REFERENCE_DB_PATH", _DEFAULT_DB_PATH))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a sqlite3 Connection; commit on success, rollback on error, always close."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row          # dict-like rows, mirrors psycopg dict_row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
