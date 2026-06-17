# src/db/create_database.py
# ---------------------------------------------------------------------------
# Create the target PostgreSQL database if it doesn't exist yet.
# ---------------------------------------------------------------------------
# Connects to the maintenance database ('postgres') using the same credentials
# as the app (loaded from .env via src.db.connection) and issues CREATE DATABASE
# for PGDATABASE. CREATE DATABASE can't run in a transaction -> autocommit.
#
# Usage:  PYTHONPATH=. python src/db/create_database.py
# Then build the schema + seed:  PYTHONPATH=. python src/db/build_reference_db.py
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import os

import psycopg

import src.db.connection  # noqa: F401  (import triggers .env loading)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_database() -> None:
    target = os.environ.get("PGDATABASE", "analytics")
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "")
    maintenance = f"host={host} port={port} dbname=postgres user={user} password={password}"

    with psycopg.connect(maintenance, autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,))
        if cur.fetchone():
            print(f"database {target!r} already exists")
        else:
            cur.execute(f'CREATE DATABASE "{target}"')
            print(f"created database {target!r}")


if __name__ == "__main__":
    create_database()
