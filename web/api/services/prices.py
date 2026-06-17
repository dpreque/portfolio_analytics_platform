# web/api/services/prices.py
# ---------------------------------------------------------------------------
# Prices service : price history for one security, split by source. Powers the
# price-viewer dashboard's "compare sources" line chart.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging

from src.db.connection import get_connection

logger = logging.getLogger(__name__)


def get_price_series(
    entity_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
    sources: list[str] | None = None,
) -> dict:
    """Return {entity, series:[{source, points:[{date, price}]}]} for one security."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT entity_id, display_name, asset_class, sector, isin, ticker, base_currency
               FROM dim_entity WHERE entity_id = %s""",
            (entity_id,),
        )
        entity_row = cur.fetchone()
        if entity_row is None:
            return {"entity": None, "series": []}
        entity = dict(entity_row)

        sql = """
            SELECT source, reference_date, price
            FROM fact_prices
            WHERE entity_id = %s
        """
        params: list = [entity_id]
        if date_from:
            sql += " AND reference_date >= %s"
            params.append(date_from)
        if date_to:
            sql += " AND reference_date <= %s"
            params.append(date_to)
        if sources:
            placeholders = ",".join("%s" for _ in sources)
            sql += f" AND source IN ({placeholders})"
            params += sources
        sql += " ORDER BY source, reference_date"

        cur.execute(sql, params)
        # group rows into one series per source (rows already source-then-date ordered)
        series: dict[str, list[dict]] = {}
        for row in cur.fetchall():
            series.setdefault(row["source"], []).append(
                {"date": row["reference_date"], "price": row["price"]}
            )

    return {
        "entity": entity,
        "series": [{"source": src, "points": pts} for src, pts in series.items()],
    }
