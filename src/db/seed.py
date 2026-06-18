# src/db/seed.py
# ---------------------------------------------------------------------------
# Deterministic sample-data generator for the REFERENCE DB (front-end dev),
# mirroring the official pgetl PostgreSQL structure:
#   dim_entity -> dim_security (+ _equity/_fund/_bond) + dim_entity_identifiers
#   series_registry (one per entity x source) -> fact_prices (series_id, date)
#   dim_portfolio (procode) -> fact_positions (security_entity_id, date, source)
#
# psycopg v3: %s placeholders, RETURNING for identity ids, executemany for bulk
# facts, native date objects for DATE columns. Deterministic (random.seed).
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import random
from datetime import date, timedelta

import psycopg

logger = logging.getLogger(__name__)

_SEED = 42
_END_DATE = date(2026, 6, 10)
_N_BUSINESS_DAYS = 90

_PRICE_SOURCE_BIAS = {"bloomberg": 0.0000, "sbs": 0.0015, "scraper": -0.0010}

# (display_name, asset_class, sector, isin, ticker, currency, country, base_price, price_sources)
_SECURITIES = [
    ("Cemex SAB CPO",            "equity", "Materials",       "MXP225611567", "CEMEXCPO", "MXN", "MX",  12.40, ["bloomberg", "sbs", "scraper"]),
    ("America Movil L",          "equity", "Communication",   "MXP001691213", "AMXL",     "MXN", "MX",  16.10, ["bloomberg", "sbs", "scraper"]),
    ("Grupo Bimbo A",            "equity", "Consumer Staples", "MXP495211262", "BIMBOA",   "MXN", "MX",  72.50, ["bloomberg", "sbs"]),
    ("Walmart de Mexico V",      "equity", "Consumer Staples", "MXP810541213", "WALMEX",   "MXN", "MX",  64.20, ["bloomberg", "sbs", "scraper"]),
    ("Femsa UBD",                "equity", "Consumer Staples", "MXP320321310", "FEMSAUBD", "MXN", "MX", 198.30, ["bloomberg", "sbs"]),
    ("Grupo Mexico B",           "equity", "Materials",        "MXP370841019", "GMEXICOB", "MXN", "MX", 102.70, ["bloomberg", "sbs", "scraper"]),
    ("Apple Inc",                "equity", "Technology",       "US0378331005", "AAPL",     "USD", "US", 224.50, ["bloomberg", "scraper"]),
    ("Microsoft Corp",           "equity", "Technology",       "US5949181045", "MSFT",     "USD", "US", 438.10, ["bloomberg", "scraper"]),
    ("Nvidia Corp",              "equity", "Technology",       "US67066G1040", "NVDA",     "USD", "US", 128.30, ["bloomberg", "scraper"]),
    ("Mexico Cetes 364d",        "bond",   "Govt",             "MX0MGO0000K9", "CETES364", "MXN", "MX",  98.85, ["bloomberg", "sbs"]),
    ("Mbono Dec-2034",           "bond",   "Govt",             "MX0MGO0000P8", "MBONO34",  "MXN", "MX",  92.40, ["bloomberg", "sbs"]),
    ("Udibono Nov-2035",         "bond",   "Govt",             "MX0SGO0000Q2", "UDI35",    "MXN", "MX", 104.20, ["bloomberg", "sbs"]),
    ("US Treasury 4.25 2034",    "bond",   "Govt",             "US91282CKW10", "T425-34",  "USD", "US",  97.60, ["bloomberg"]),
    ("Pemex 6.5 2027",           "bond",   "Corporate",        "US71654QBG10", "PEMEX27",  "USD", "MX",  95.10, ["bloomberg"]),
    ("Cemex 5.45 2029",          "bond",   "Corporate",        "US151290BX80", "CEMEX29",  "USD", "MX",  98.20, ["bloomberg"]),
    ("Femsa 3.5 2028",           "bond",   "Corporate",        "US344419AA98", "FEMSA28",  "USD", "MX",  94.70, ["bloomberg"]),
    ("iShares MSCI Mexico ETF",  "fund",   "Equity Fund",      "US4642868065", "EWW",      "USD", "US",  58.90, ["bloomberg", "scraper"]),
    ("iShares Core S&P500 ETF",  "fund",   "Equity Fund",      "US4642872000", "IVV",      "USD", "US", 545.30, ["bloomberg", "scraper"]),
    ("Vanguard Total Bond ETF",  "fund",   "Bond Fund",        "US9219378356", "BND",      "USD", "US",  72.80, ["bloomberg", "scraper"]),
    ("BlackRock Liquidity MXN",  "fund",   "Money Market",     "MX1MMF000123", "BLKMMXN",  "MXN", "MX",   1.00, ["sbs"]),
    ("Naftrac ISHRS",            "fund",   "Equity Fund",      "MX1NAFT00010", "NAFTRAC",  "MXN", "MX",  56.40, ["bloomberg", "sbs", "scraper"]),
    ("Alfa A",                   "equity", "Industrials",      "MXP000511016", "ALFAA",    "MXN", "MX",  13.20, ["bloomberg", "sbs"]),
]

# (display_name, currency) — synthetic per-currency cash entities (entity_type='cash')
_CASH = [("Cash MXN", "MXN"), ("Cash USD", "USD")]

# (procode, source, portfolio_type, display_name, base_currency, status)
_PORTFOLIOS = [
    ("PF-PENS-01", "fms", "own_account",      "Pension Fund Conservative", "MXN", "active"),
    ("PF-PENS-02", "fms", "own_account",      "Pension Fund Growth",       "MXN", "active"),
    ("PF-REG-77",  "sbs", "regulator_filing", "SBS Regulatory Filing 77",  "MXN", "active"),
    ("PF-ETF-EWW", "bloomberg", "etf",        "EWW Replication Sleeve",    "USD", "active"),
]

_SNAPSHOT_TARGETS = [date(2026, 3, 31), date(2026, 4, 30), date(2026, 5, 29), date(2026, 6, 10)]


def _business_days(end: date, n: int) -> list[date]:
    days: list[date] = []
    d = end
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return sorted(days)


def _vol_for(asset_class: str) -> float:
    return {"equity": 0.013, "bond": 0.003, "fund": 0.009, "cash": 0.0}.get(asset_class, 0.01)


def seed(conn: psycopg.Connection) -> dict[str, int]:
    """Populate all reference tables in the normalized pgetl shape."""
    rng = random.Random(_SEED)
    cur = conn.cursor()
    days = _business_days(_END_DATE, _N_BUSINESS_DAYS)

    price_rows: list[tuple] = []                       # (series_id, date, price, source)
    price_lookup: dict[tuple[int, date], float] = {}   # (entity_id, date) -> clean mid price
    entities: list[dict] = []

    # --- securities: dim_entity -> dim_security (+ extension) + identifiers ----
    for (name, ac, sector, isin, ticker, ccy, country, base, psources) in _SECURITIES:
        entity_type = "fund" if ac == "fund" else "security"
        cur.execute(
            "INSERT INTO dim_entity (procode, entity_type, name) VALUES (%s, %s, %s) RETURNING entity_id",
            (ticker, entity_type, name),
        )
        eid = cur.fetchone()["entity_id"]

        cur.execute(
            """INSERT INTO dim_security
               (entity_id, ticker, name, short_name, security_name, currency, country, market_sector, security_type)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING security_id""",
            (eid, ticker, name, ticker, name, ccy, country, sector, ac),
        )
        sid = cur.fetchone()["security_id"]

        if ac == "equity":
            cur.execute("INSERT INTO dim_security_equity (security_id, sector) VALUES (%s, %s)", (sid, sector))
        elif ac == "fund":
            cur.execute(
                """INSERT INTO dim_security_fund (security_id, fund_type, asset_class, geography, objective)
                   VALUES (%s, %s, %s, %s, %s)""",
                (sid, "ETF", sector, country, "Index replication"),
            )
        elif ac == "bond":
            cur.execute(
                """INSERT INTO dim_security_bond (security_id, issue_date, maturity_date, coupon_rate, rating)
                   VALUES (%s, %s, %s, %s, %s)""",
                (sid, date(2022, 1, 15), date(2030, 12, 31), round(rng.uniform(3.0, 8.0), 3), "A"),
            )

        cur.execute(
            "INSERT INTO dim_entity_identifiers (entity_id, id_type, id_value, source, is_primary) VALUES (%s,%s,%s,%s,%s)",
            (eid, "isin", isin, "bloomberg", True),
        )
        cur.execute(
            "INSERT INTO dim_entity_identifiers (entity_id, id_type, id_value, source, is_primary) VALUES (%s,%s,%s,%s,%s)",
            (eid, "parsekyable", ticker, "bloomberg", False),
        )
        entities.append({"id": eid, "ac": ac, "sources": psources, "ccy": ccy, "base": base, "ticker": ticker})

    # --- cash entities (no dim_security) --------------------------------------
    cash_entities: dict[str, int] = {}
    for (name, ccy) in _CASH:
        cur.execute(
            "INSERT INTO dim_entity (procode, entity_type, name) VALUES (%s, 'cash', %s) RETURNING entity_id",
            (f"CASH_{ccy}", name),
        )
        eid = cur.fetchone()["entity_id"]
        cur.execute(
            "INSERT INTO dim_entity_identifiers (entity_id, id_type, id_value, source, is_primary) VALUES (%s,%s,%s,%s,%s)",
            (eid, "currency_cash", ccy, "sbs", True),
        )
        cash_entities[ccy] = eid

    # --- series_registry + fact_prices ----------------------------------------
    for ent in entities:
        vol = _vol_for(ent["ac"])
        path = [ent["base"]]
        for _ in range(len(days) - 1):
            path.append(max(0.01, path[-1] * (1 + rng.gauss(0.0002, vol))))
        for i, d in enumerate(days):
            price_lookup[(ent["id"], d)] = path[i]
        for src in ent["sources"]:
            cur.execute(
                """INSERT INTO series_registry (entity_id, field, domain, source, frequency, status)
                   VALUES (%s, 'PX_LAST', 'prices', %s, 'daily', 'active') RETURNING series_id""",
                (ent["id"], src),
            )
            series_id = cur.fetchone()["series_id"]
            bias = _PRICE_SOURCE_BIAS.get(src, 0.0)
            for i, d in enumerate(days):
                px = round(path[i] * (1 + bias + rng.gauss(0, vol * 0.15)), 4)
                price_rows.append((series_id, d, px, src))

    for ccy, eid in cash_entities.items():
        cur.execute(
            """INSERT INTO series_registry (entity_id, field, domain, source, frequency, status)
               VALUES (%s, 'PX_LAST', 'prices', 'sbs', 'daily', 'active') RETURNING series_id""",
            (eid,),
        )
        series_id = cur.fetchone()["series_id"]
        for d in days:
            price_lookup[(eid, d)] = 1.0
            price_rows.append((series_id, d, 1.0, "sbs"))

    cur.executemany(
        "INSERT INTO fact_prices (series_id, date, price, source) VALUES (%s, %s, %s, %s)",
        price_rows,
    )

    # --- dim_portfolio --------------------------------------------------------
    portfolios: list[dict] = []
    eww_entity = next(e["id"] for e in entities if e["ticker"] == "EWW")
    for (procode, src, ptype, name, ccy, status) in _PORTFOLIOS:
        parent = eww_entity if ptype == "etf" else None
        cur.execute(
            """INSERT INTO dim_portfolio
               (procode, source, portfolio_type, display_name, base_currency, parent_entity_id, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING portfolio_id""",
            (procode, src, ptype, name, ccy, parent, status),
        )
        portfolios.append({"id": cur.fetchone()["portfolio_id"], "source": src, "ccy": ccy, "type": ptype})

    # snap snapshot targets to the nearest trading day <= target
    day_set = set(days)
    snapshots: list[date] = []
    for t in _SNAPSHOT_TARGETS:
        d = t
        while d not in day_set:
            d -= timedelta(days=1)
        snapshots.append(d)

    # --- fact_positions -------------------------------------------------------
    pos_rows: list[tuple] = []
    for pf in portfolios:
        eligible = list(entities)
        rng.shuffle(eligible)
        if pf["type"] == "etf":
            universe = [e for e in entities if e["ac"] in ("equity", "fund")][:10]
        else:
            universe = eligible[:12]
        cash_eid = cash_entities.get(pf["ccy"], cash_entities["MXN"])
        base_qty = {e["id"]: rng.uniform(5_000, 250_000) for e in universe}
        cash_qty = rng.uniform(500_000, 5_000_000)
        for d in snapshots:
            holdings: list[tuple[int, float, float]] = []
            for e in universe:
                px = price_lookup.get((e["id"], d))
                if px is None:
                    continue
                qty = base_qty[e["id"]]
                holdings.append((e["id"], qty, qty * px))
            holdings.append((cash_eid, cash_qty, cash_qty * 1.0))
            total_mv = sum(h[2] for h in holdings) or 1.0
            for (eid, qty, mv) in holdings:
                pos_rows.append((
                    pf["id"], eid, d, pf["source"],
                    round(qty, 2), round(mv, 2), round(mv * 0.95, 2), 0.0,
                    round(mv / total_mv, 6), round(price_lookup.get((eid, d), 0.0), 4),
                    pf["ccy"], None, None,
                ))
    cur.executemany(
        """INSERT INTO fact_positions
           (portfolio_id, security_entity_id, date, source, quantity, market_value,
            cost_basis, accrued_interest, weight, price_used, currency, yield_to_maturity, duration)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        pos_rows,
    )

    def _count(table: str) -> int:
        cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
        return cur.fetchone()["n"]

    counts = {t: _count(t) for t in
              ("dim_entity", "dim_security", "dim_entity_identifiers",
               "series_registry", "fact_prices", "dim_portfolio", "fact_positions")}
    logger.info(f"seeded reference DB: {counts}")
    return counts
