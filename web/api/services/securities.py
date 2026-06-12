# web/api/services/securities.py
# ---------------------------------------------------------------------------
# Securities service : read-side lookups over dim_entity for the price-viewer
# picker. The API is the semantic layer -- callers never see raw table shape.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging

from src.db.session import get_connection

logger = logging.getLogger(__name__)


def list_securities(search: str | None = None, limit: int = 100) -> list[dict]:
    """Return securities for a picker, optionally filtered by name/ticker/ISIN."""
    sql = """
        SELECT entity_id, display_name, asset_class, sector, isin, ticker, base_currency
        FROM dim_entity
    """
    params: list = []
    if search:
        sql += " WHERE display_name LIKE ? OR ticker LIKE ? OR isin LIKE ?"
        like = f"%{search}%"
        params += [like, like, like]
    sql += " ORDER BY display_name LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
