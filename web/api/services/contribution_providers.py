# web/api/services/contribution_providers.py
# ---------------------------------------------------------------------------
# Contribution data-access providers (the migration seam for fact_contribution).
# ---------------------------------------------------------------------------
# Two interchangeable providers produce the SAME response shape:
#
#   DerivedContributionProvider  -- today. Computes contribution on the fly from
#                                   fact_positions x fact_prices (single-period
#                                   buy-and-hold approximation).
#   FactContributionProvider     -- future. Reads precomputed rows straight from
#                                   the fact_contribution table.
#
# `get_contribution_provider()` picks the fact-table provider automatically once
# fact_contribution has data, else falls back to derived. The route and the
# front end never change -- migrating is a data event, not a code change.
#
# To force a provider (tests / ops), set env CONTRIBUTION_PROVIDER=derived|fact.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Protocol

from src.db.connection import get_connection

logger = logging.getLogger(__name__)


class ContributionProvider(Protocol):
    """Read-side contract for contribution data. Both providers return:
    {portfolio, period, snapshot_date, source, portfolio_return, holdings[], by_asset_class[]}.
    """

    def get_contribution(
        self, portfolio_id: int, date_from: str, date_to: str, source: str | None
    ) -> dict: ...


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _portfolio(cur: sqlite3.Cursor, portfolio_id: int) -> dict | None:
    cur.execute(
        """SELECT portfolio_id, internal_code, display_name, base_currency
           FROM dim_portfolio WHERE portfolio_id = ?""",
        (portfolio_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _bucket_contribution(holdings: list[dict]) -> list[dict]:
    """Aggregate contribution + weight by asset_class, descending by contribution."""
    agg: dict[str, dict] = {}
    for h in holdings:
        k = h["asset_class"] or "unknown"
        b = agg.setdefault(k, {"asset_class": k, "weight": 0.0, "contribution": 0.0})
        b["weight"] += h["weight"]
        b["contribution"] += h["contribution"]
    rows = sorted(agg.values(), key=lambda r: r["contribution"], reverse=True)
    for r in rows:
        r["weight"] = round(r["weight"], 6)
        r["contribution"] = round(r["contribution"], 6)
    return rows


def _shape(portfolio: dict, date_from: str, date_to: str, source: str | None,
           snapshot_date: str | None, holdings: list[dict]) -> dict:
    """Assemble the common response envelope from a list of per-holding rows."""
    portfolio_return = round(sum(h["contribution"] for h in holdings), 6)
    by_asset_class = _bucket_contribution(holdings)
    holdings = sorted(holdings, key=lambda h: h["contribution"], reverse=True)
    return {
        "portfolio": portfolio,
        "period": {"from": date_from, "to": date_to},
        "snapshot_date": snapshot_date,
        "source": source,
        "portfolio_return": portfolio_return,
        "holdings": holdings,
        "by_asset_class": by_asset_class,
    }


# ---------------------------------------------------------------------------
# Derived provider (current): fact_positions x fact_prices
# ---------------------------------------------------------------------------
class DerivedContributionProvider:
    """contribution_i = weight_i(d0) * (price_i(d1)/price_i(d0) - 1).

    Beginning weights from the position snapshot on/before d0; prices the latest
    on/before each endpoint. Ignores intra-period rebalancing -- fine as a
    reference, and isolated here so it is easy to retire.
    """

    def get_contribution(self, portfolio_id, date_from, date_to, source=None) -> dict:
        with get_connection() as conn:
            cur = conn.cursor()
            portfolio = _portfolio(cur, portfolio_id)
            if portfolio is None:
                return {"portfolio": None}

            cur.execute(
                """SELECT MAX(reference_date) AS d FROM fact_positions
                   WHERE portfolio_id = ? AND reference_date <= ?""",
                (portfolio_id, date_from),
            )
            snap = cur.fetchone()["d"]
            if snap is None:
                return _shape(portfolio, date_from, date_to, source, None, [])

            cur.execute(
                """SELECT p.entity_id, e.display_name, e.asset_class, e.sector, p.weight
                   FROM fact_positions p
                   JOIN dim_entity e ON e.entity_id = p.entity_id
                   WHERE p.portfolio_id = ? AND p.reference_date = ?""",
                (portfolio_id, snap),
            )
            positions = [dict(row) for row in cur.fetchall()]

            holdings: list[dict] = []
            for pos in positions:
                p0 = _price_at(cur, pos["entity_id"], date_from, source)
                p1 = _price_at(cur, pos["entity_id"], date_to, source)
                ret = (p1 / p0 - 1.0) if (p0 and p1 and p0 != 0) else 0.0
                weight = pos["weight"] or 0.0
                holdings.append({
                    "entity_id": pos["entity_id"],
                    "display_name": pos["display_name"],
                    "asset_class": pos["asset_class"],
                    "sector": pos["sector"],
                    "weight": round(weight, 6),
                    "return": round(ret, 6),
                    "contribution": round(weight * ret, 6),
                })

        return _shape(portfolio, date_from, date_to, source, snap, holdings)


def _price_at(cur: sqlite3.Cursor, entity_id: int, on_or_before: str, source: str | None) -> float | None:
    """Latest price for entity on-or-before a date. Prefers `source`, else bloomberg, else any."""
    if source:
        cur.execute(
            """SELECT price FROM fact_prices
               WHERE entity_id = ? AND reference_date <= ? AND source = ?
               ORDER BY reference_date DESC LIMIT 1""",
            (entity_id, on_or_before, source),
        )
        row = cur.fetchone()
        if row:
            return row["price"]
    cur.execute(
        """SELECT price FROM fact_prices
           WHERE entity_id = ? AND reference_date <= ?
           ORDER BY (source = 'bloomberg') DESC, reference_date DESC LIMIT 1""",
        (entity_id, on_or_before),
    )
    row = cur.fetchone()
    return row["price"] if row else None


# ---------------------------------------------------------------------------
# Fact provider (future): read precomputed fact_contribution rows
# ---------------------------------------------------------------------------
class FactContributionProvider:
    """Reads contribution straight from fact_contribution for the exact period.

    Note: contributions are stored per precomputed period, so date_from/date_to
    must match a stored (period_start, period_end). A future endpoint can expose
    the available periods; until then this provider activates only when the
    table holds data for the requested period.
    """

    def get_contribution(self, portfolio_id, date_from, date_to, source=None) -> dict:
        with get_connection() as conn:
            cur = conn.cursor()
            portfolio = _portfolio(cur, portfolio_id)
            if portfolio is None:
                return {"portfolio": None}

            sql = """
                SELECT c.entity_id, e.display_name, e.asset_class, e.sector,
                       c.weight, c.period_return AS return, c.contribution
                FROM fact_contribution c
                JOIN dim_entity e ON e.entity_id = c.entity_id
                WHERE c.portfolio_id = ? AND c.period_start = ? AND c.period_end = ?
            """
            params: list = [portfolio_id, date_from, date_to]
            if source:
                sql += " AND c.source = ?"
                params.append(source)

            cur.execute(sql, params)
            holdings = [{
                "entity_id": r["entity_id"],
                "display_name": r["display_name"],
                "asset_class": r["asset_class"],
                "sector": r["sector"],
                "weight": round(r["weight"] or 0.0, 6),
                "return": round(r["return"] or 0.0, 6),
                "contribution": round(r["contribution"] or 0.0, 6),
            } for r in cur.fetchall()]

        return _shape(portfolio, date_from, date_to, source, date_from, holdings)


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------
def _fact_table_has_data() -> bool:
    """True if fact_contribution exists and holds at least one row."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='fact_contribution'"
            )
            if cur.fetchone() is None:
                return False
            cur.execute("SELECT 1 FROM fact_contribution LIMIT 1")
            return cur.fetchone() is not None
    except sqlite3.Error as exc:
        logger.warning(f"fact_contribution probe failed, using derived provider: {exc}")
        return False


def get_contribution_provider() -> ContributionProvider:
    """Pick the provider: explicit env override, else fact-table if populated, else derived."""
    override = os.environ.get("CONTRIBUTION_PROVIDER", "").lower()
    if override == "fact":
        return FactContributionProvider()
    if override == "derived":
        return DerivedContributionProvider()
    return FactContributionProvider() if _fact_table_has_data() else DerivedContributionProvider()
