# src/db/build_reference_db.py
# ---------------------------------------------------------------------------
# Build the reference PostgreSQL DB: drop the known tables, apply every
# schema/NN_*.sql in order, then seed deterministic sample data.
# ---------------------------------------------------------------------------
# Usage:  PYTHONPATH=. python src/db/build_reference_db.py
# Connection comes from the environment (see src/db/connection.get_conninfo):
#   DATABASE_URL=...  or  PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD
# The target database must already exist (e.g. `createdb analytics`); this script
# creates the tables. Safe to re-run: drops + recreates from scratch.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import re
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from src.db.connection import get_conninfo
from src.db.seed import seed

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_SCHEMA_DIR = Path(__file__).resolve().parent / "schema"
# Drop order: facts/children first, then dimensions (CASCADE also clears FKs).
_DROP_ORDER = [
    "fact_positions", "fact_prices", "series_registry",
    "dim_entity_identifiers", "dim_portfolio",
    "dim_security_equity", "dim_security_fund", "dim_security_bond",
    "dim_security", "dim_entity",
    # staging landing zones (FK-free)
    "stg_security_bloomberg", "stg_prices_bloomberg",
    "stg_prices_sbs_vector_completo", "stg_prices_sbs_rf_local",
    "stg_prices_sbs_rf_exterior", "stg_prices_sbs_tipo_cambio",
    "stg_prices_sbs_dividendos", "stg_positions_fms",
]


def _statements(sql_text: str) -> list[str]:
    """Split a schema file into statements. Strips `--` comments FIRST so a ';'
    inside a comment can't split a statement, then splits on ';'."""
    no_comments = "\n".join(re.sub(r"--.*$", "", line) for line in sql_text.splitlines())
    return [chunk.strip() for chunk in no_comments.split(";") if chunk.strip()]


def build() -> None:
    conninfo = get_conninfo()
    with psycopg.connect(conninfo, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for table in _DROP_ORDER:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            logger.info(f"dropped existing tables: {', '.join(_DROP_ORDER)}")

            applied = []
            for sql_file in sorted(_SCHEMA_DIR.glob("*.sql")):
                for stmt in _statements(sql_file.read_text(encoding="utf-8")):
                    cur.execute(stmt)
                applied.append(sql_file.name)
            logger.info(f"applied schema files: {', '.join(applied)}")

        counts = seed(conn)
        conn.commit()

    print(f"\nReference DB built (postgres: {conninfo.split('password=')[0].strip()})")
    print("Row counts:")
    for table, n in counts.items():
        print(f"  {table:28s} {n:>7,}")


if __name__ == "__main__":
    build()
