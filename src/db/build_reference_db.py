# src/db/build_reference_db.py
# ---------------------------------------------------------------------------
# Build the reference SQLite DB: (re)create data/reference.db, apply every
# schema/NN_*.sql in order, then seed deterministic sample data.
# ---------------------------------------------------------------------------
# Usage:  python src/db/build_reference_db.py
# Safe to re-run: drops and recreates the DB file from scratch.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from src.db.seed import seed
from src.db.connection import get_db_path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_SCHEMA_DIR = Path(__file__).resolve().parent / "schema"


def build() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
        logger.info(f"removed existing {db_path}")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        applied = []
        for sql_file in sorted(_SCHEMA_DIR.glob("*.sql")):
            conn.executescript(sql_file.read_text(encoding="utf-8"))
            applied.append(sql_file.name)
        logger.info(f"applied schema files: {', '.join(applied)}")

        counts = seed(conn)
        conn.commit()
    finally:
        conn.close()

    print(f"\nReference DB built at: {db_path}")
    print("Row counts:")
    for table, n in counts.items():
        print(f"  {table:28s} {n:>7,}")


if __name__ == "__main__":
    build()
