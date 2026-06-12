# web/api/services/portfolios.py
# ---------------------------------------------------------------------------
# Portfolios service : portfolio list + available position dates.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging

from src.db.session import get_connection

logger = logging.getLogger(__name__)


def list_portfolios() -> list[dict]:
    """All portfolios, for the portfolio picker."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT portfolio_id, internal_code, source, portfolio_type,
                      display_name, base_currency, status
               FROM dim_portfolio
               ORDER BY display_name"""
        )
        return [dict(row) for row in cur.fetchall()]


def get_position_dates(portfolio_id: int) -> list[str]:
    """Distinct snapshot dates that have positions, most recent first."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT DISTINCT reference_date
               FROM fact_positions
               WHERE portfolio_id = ?
               ORDER BY reference_date DESC""",
            (portfolio_id,),
        )
        return [row["reference_date"] for row in cur.fetchall()]
