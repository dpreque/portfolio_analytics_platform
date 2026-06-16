# web/api/services/positions.py
# ---------------------------------------------------------------------------
# Positions service : enriched holdings for a portfolio on a given date.
# ---------------------------------------------------------------------------
# Joins fact_positions -> dim_entity (security names / asset class) and returns
# both the per-holding rows and summary buckets (by asset_class, by currency)
# for the positioning dashboard's breakdown chart. Endpoint models a business
# concept ("holdings"), never the raw fact table.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging

from src.db.connection import get_connection

logger = logging.getLogger(__name__)


def get_holdings(portfolio_id: int, reference_date: str | None = None) -> dict:
    """Return enriched holdings + summary for a portfolio on a date.

    If reference_date is omitted, uses the latest available snapshot.
    """
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """SELECT portfolio_id, internal_code, source, portfolio_type,
                      display_name, base_currency, status
               FROM dim_portfolio WHERE portfolio_id = ?""",
            (portfolio_id,),
        )
        pf_row = cur.fetchone()
        if pf_row is None:
            return {"portfolio": None, "reference_date": None, "holdings": [], "summary": {}}
        portfolio = dict(pf_row)

        # Snap to the latest snapshot on/before the requested date (or the latest
        # overall if none given), so any free-form date from the range picker works.
        if reference_date is None:
            cur.execute(
                "SELECT MAX(reference_date) AS d FROM fact_positions WHERE portfolio_id = ?",
                (portfolio_id,),
            )
            reference_date = cur.fetchone()["d"]
        else:
            cur.execute(
                """SELECT MAX(reference_date) AS d FROM fact_positions
                   WHERE portfolio_id = ? AND reference_date <= ?""",
                (portfolio_id, reference_date),
            )
            reference_date = cur.fetchone()["d"]

        cur.execute(
            """SELECT p.entity_id, e.display_name, e.asset_class, e.sector, e.isin, e.ticker,
                      p.source, p.quantity, p.market_value, p.weight, p.price_used, p.currency
               FROM fact_positions p
               JOIN dim_entity e ON e.entity_id = p.entity_id
               WHERE p.portfolio_id = ? AND p.reference_date = ?
               ORDER BY p.market_value DESC""",
            (portfolio_id, reference_date),
        )
        holdings = [dict(row) for row in cur.fetchall()]

    total_mv = sum(h["market_value"] or 0.0 for h in holdings)
    by_asset_class = _bucket(holdings, "asset_class")
    by_currency = _bucket(holdings, "currency")

    return {
        "portfolio": portfolio,
        "reference_date": reference_date,
        "total_market_value": round(total_mv, 2),
        "holdings": holdings,
        "summary": {"by_asset_class": by_asset_class, "by_currency": by_currency},
    }


def _bucket(holdings: list[dict], key: str) -> list[dict]:
    """Aggregate market_value + weight by a holding attribute, descending."""
    agg: dict[str, dict] = {}
    for h in holdings:
        k = h.get(key) or "unknown"
        b = agg.setdefault(k, {"key": k, "market_value": 0.0, "weight": 0.0})
        b["market_value"] += h["market_value"] or 0.0
        b["weight"] += h["weight"] or 0.0
    rows = sorted(agg.values(), key=lambda r: r["market_value"], reverse=True)
    for r in rows:
        r["market_value"] = round(r["market_value"], 2)
        r["weight"] = round(r["weight"], 6)
    return rows
