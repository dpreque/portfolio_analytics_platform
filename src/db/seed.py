# src/db/seed.py
# ---------------------------------------------------------------------------
# Deterministic sample-data generator for the REFERENCE DB (front-end dev).
# ---------------------------------------------------------------------------
# Produces enough data for all three dashboards to render meaningfully:
#   - dim_entity / dim_entity_identifiers : ~24 securities across asset classes
#   - dim_portfolio                       : 4 portfolios (own_account / filing / etf)
#   - fact_prices                         : ~90 business days, 2-3 sources each
#   - fact_positions                      : monthly snapshots with MV-based weights
#
# Deterministic (random.seed) so rebuilds are reproducible. This is throwaway
# scaffolding; the authoritative data lives on the ETL machine.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import random
import sqlite3
from datetime import date, timedelta

logger = logging.getLogger(__name__)

_SEED = 42
_END_DATE = date(2026, 6, 10)
_N_BUSINESS_DAYS = 90

# Price sources we simulate, with a small systematic bias per source so the
# "by source" comparison shows visible (but small) dispersion.
_PRICE_SOURCE_BIAS = {
    "bloomberg": 0.0000,
    "sbs": 0.0015,
    "scraper": -0.0010,
}

# (display_name, asset_class, sector, isin, ticker, currency, country, base_price, price_sources)
_SECURITIES = [
    ("Cemex SAB CPO",            "equity", "Materials",      "MXP225611567", "CEMEXCPO", "MXN", "MX",  12.40, ["bloomberg", "sbs", "scraper"]),
    ("America Movil L",          "equity", "Communication",  "MXP001691213", "AMXL",     "MXN", "MX",  16.10, ["bloomberg", "sbs", "scraper"]),
    ("Grupo Bimbo A",            "equity", "Consumer Staples","MXP495211262","BIMBOA",   "MXN", "MX",  72.50, ["bloomberg", "sbs"]),
    ("Walmart de Mexico V",      "equity", "Consumer Staples","MXP810541213","WALMEX",   "MXN", "MX",  64.20, ["bloomberg", "sbs", "scraper"]),
    ("Femsa UBD",                "equity", "Consumer Staples","MXP320321310","FEMSAUBD", "MXN", "MX", 198.30, ["bloomberg", "sbs"]),
    ("Grupo Mexico B",           "equity", "Materials",      "MXP370841019", "GMEXICOB", "MXN", "MX", 102.70, ["bloomberg", "sbs", "scraper"]),
    ("Apple Inc",                "equity", "Technology",     "US0378331005", "AAPL",     "USD", "US", 224.50, ["bloomberg", "scraper"]),
    ("Microsoft Corp",           "equity", "Technology",     "US5949181045", "MSFT",     "USD", "US", 438.10, ["bloomberg", "scraper"]),
    ("Nvidia Corp",              "equity", "Technology",     "US67066G1040", "NVDA",     "USD", "US", 128.30, ["bloomberg", "scraper"]),
    ("Mexico Cetes 364d",        "bond",   "Govt",           "MX0MGO0000K9", "CETES364", "MXN", "MX",  98.85, ["bloomberg", "sbs"]),
    ("Mbono Dec-2034",           "bond",   "Govt",           "MX0MGO0000P8", "MBONO34",  "MXN", "MX",  92.40, ["bloomberg", "sbs"]),
    ("Udibono Nov-2035",         "bond",   "Govt",           "MX0SGO0000Q2", "UDI35",    "MXN", "MX", 104.20, ["bloomberg", "sbs"]),
    ("US Treasury 4.25 2034",    "bond",   "Govt",           "US91282CKW10", "T425-34",  "USD", "US",  97.60, ["bloomberg"]),
    ("Pemex 6.5 2027",           "bond",   "Corporate",      "US71654QBG10", "PEMEX27",  "USD", "MX",  95.10, ["bloomberg"]),
    ("Cemex 5.45 2029",          "bond",   "Corporate",      "US151290BX80", "CEMEX29",  "USD", "MX",  98.20, ["bloomberg"]),
    ("Femsa 3.5 2028",           "bond",   "Corporate",      "US344419AA98", "FEMSA28",  "USD", "MX",  94.70, ["bloomberg"]),
    ("iShares MSCI Mexico ETF",  "fund",   "Equity Fund",    "US4642868065", "EWW",      "USD", "US",  58.90, ["bloomberg", "scraper"]),
    ("iShares Core S&P500 ETF",  "fund",   "Equity Fund",    "US4642872000", "IVV",      "USD", "US", 545.30, ["bloomberg", "scraper"]),
    ("Vanguard Total Bond ETF",  "fund",   "Bond Fund",      "US9219378356", "BND",      "USD", "US",  72.80, ["bloomberg", "scraper"]),
    ("BlackRock Liquidity MXN",  "fund",   "Money Market",   "MX1MMF000123", "BLKMMXN",  "MXN", "MX",   1.00, ["sbs"]),
    ("Naftrac ISHRS",            "fund",   "Equity Fund",    "MX1NAFT00010", "NAFTRAC",  "MXN", "MX",  56.40, ["bloomberg", "sbs", "scraper"]),
    ("Alfa A",                   "equity", "Industrials",    "MXP000511016", "ALFAA",    "MXN", "MX",  13.20, ["bloomberg", "sbs"]),
]

# Synthetic per-currency cash entities (id_type='currency_cash').
_CASH = [
    ("Cash MXN", "MXN"),
    ("Cash USD", "USD"),
]

# (internal_code, source, portfolio_type, display_name, base_currency, status)
_PORTFOLIOS = [
    ("PF-PENS-01", "fms", "own_account",      "Pension Fund Conservative", "MXN", "active"),
    ("PF-PENS-02", "fms", "own_account",      "Pension Fund Growth",       "MXN", "active"),
    ("PF-REG-77",  "sbs", "regulator_filing", "SBS Regulatory Filing 77",  "MXN", "active"),
    ("PF-ETF-EWW", "bloomberg", "etf",        "EWW Replication Sleeve",    "USD", "active"),
]

# Snapshot dates for positions (will be snapped to the nearest trading day <=).
_SNAPSHOT_TARGETS = [
    date(2026, 3, 31),
    date(2026, 4, 30),
    date(2026, 5, 29),
    date(2026, 6, 10),
]


def _business_days(end: date, n: int) -> list[date]:
    """Return n business days ending at `end` (inclusive), ascending."""
    days: list[date] = []
    d = end
    while len(days) < n:
        if d.weekday() < 5:        # Mon-Fri
            days.append(d)
        d -= timedelta(days=1)
    return sorted(days)


def _vol_for(asset_class: str) -> float:
    return {"equity": 0.013, "bond": 0.003, "fund": 0.009, "cash": 0.0}.get(asset_class, 0.01)


def seed(conn: sqlite3.Connection) -> dict[str, int]:
    """Populate all reference tables. Returns row counts per table."""
    rng = random.Random(_SEED)
    cur = conn.cursor()
    days = _business_days(_END_DATE, _N_BUSINESS_DAYS)
    day_strs = [d.isoformat() for d in days]

    # --- dim_entity + identifiers -----------------------------------------
    entities: list[dict] = []        # entity_id, asset_class, price_sources, currency, base_price
    for (name, ac, sector, isin, ticker, ccy, country, base, psources) in _SECURITIES:
        cur.execute(
            """INSERT INTO dim_entity
               (display_name, asset_class, sector, isin, ticker, base_currency, country)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, ac, sector, isin, ticker, ccy, country),
        )
        eid = cur.lastrowid
        cur.execute("INSERT INTO dim_entity_identifiers (entity_id, id_type, id_value) VALUES (?,?,?)",
                    (eid, "isin", isin))
        cur.execute("INSERT INTO dim_entity_identifiers (entity_id, id_type, id_value) VALUES (?,?,?)",
                    (eid, "bloomberg_ticker", ticker))
        entities.append({"id": eid, "ac": ac, "sources": psources, "ccy": ccy, "base": base})

    cash_entities: dict[str, int] = {}
    for (name, ccy) in _CASH:
        cur.execute(
            """INSERT INTO dim_entity
               (display_name, asset_class, sector, isin, ticker, base_currency, country)
               VALUES (?, 'cash', NULL, NULL, NULL, ?, NULL)""",
            (name, ccy),
        )
        eid = cur.lastrowid
        cur.execute("INSERT INTO dim_entity_identifiers (entity_id, id_type, id_value) VALUES (?,?,?)",
                    (eid, "currency_cash", ccy))
        cash_entities[ccy] = eid

    # --- fact_prices : random-walk path per security, dispersed per source --
    price_rows: list[tuple] = []
    # price_lookup[(entity_id, date_str)] -> reference price (bloomberg-ish mid) for MV calc
    price_lookup: dict[tuple[int, str], float] = {}
    for ent in entities:
        vol = _vol_for(ent["ac"])
        path = [ent["base"]]
        for _ in range(len(days) - 1):
            drift = 0.0002
            ret = rng.gauss(drift, vol)
            path.append(max(0.01, path[-1] * (1 + ret)))
        for i, dstr in enumerate(day_strs):
            mid = path[i]
            price_lookup[(ent["id"], dstr)] = mid
            for src in ent["sources"]:
                bias = _PRICE_SOURCE_BIAS.get(src, 0.0)
                noise = rng.gauss(0, vol * 0.15)
                px = round(mid * (1 + bias + noise), 4)
                price_rows.append((ent["id"], src, dstr, px, ent["ccy"], "close"))
    cur.executemany(
        """INSERT INTO fact_prices (entity_id, source, reference_date, price, currency, price_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        price_rows,
    )
    # cash trades flat at par in its currency, single 'sbs' source
    for ccy, eid in cash_entities.items():
        for dstr in day_strs:
            price_lookup[(eid, dstr)] = 1.0
            cur.execute(
                """INSERT INTO fact_prices (entity_id, source, reference_date, price, currency, price_type)
                   VALUES (?, 'sbs', ?, 1.0, ?, 'close')""",
                (eid, dstr, ccy),
            )

    # --- dim_portfolio ----------------------------------------------------
    portfolios: list[dict] = []
    eww_entity = next(e["id"] for e, spec in zip(entities, _SECURITIES) if spec[4] == "EWW")
    for (code, src, ptype, name, ccy, status) in _PORTFOLIOS:
        parent = eww_entity if ptype == "etf" else None
        cur.execute(
            """INSERT INTO dim_portfolio
               (internal_code, source, portfolio_type, display_name, base_currency, parent_entity_id, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (code, src, ptype, name, ccy, parent, status),
        )
        portfolios.append({"id": cur.lastrowid, "source": src, "ccy": ccy, "type": ptype})

    # snap snapshot targets to nearest trading day <= target
    day_set = set(day_strs)
    snapshots: list[str] = []
    for t in _SNAPSHOT_TARGETS:
        d = t
        while d.isoformat() not in day_set:
            d -= timedelta(days=1)
        snapshots.append(d.isoformat())

    # --- fact_positions : pick holdings per portfolio, compute MV + weight --
    pos_rows: list[tuple] = []
    for pf in portfolios:
        # choose a holdings universe per portfolio (deterministic subset)
        eligible = [e for e in entities]
        rng.shuffle(eligible)
        if pf["type"] == "etf":
            universe = [e for e in entities if e["ac"] in ("equity", "fund")][:10]
        else:
            universe = eligible[:12]
        # always include a cash leg in the portfolio's base currency
        cash_eid = cash_entities.get(pf["ccy"], cash_entities["MXN"])
        # stable base quantities per holding (so the portfolio has continuity over time)
        base_qty = {e["id"]: rng.uniform(5_000, 250_000) for e in universe}
        cash_qty = rng.uniform(500_000, 5_000_000)
        for dstr in snapshots:
            holdings: list[tuple[int, float, float]] = []   # (entity_id, qty, mv)
            for e in universe:
                px = price_lookup.get((e["id"], dstr))
                if px is None:
                    continue
                qty = base_qty[e["id"]]
                mv = qty * px
                holdings.append((e["id"], qty, mv))
            # cash leg
            holdings.append((cash_eid, cash_qty, cash_qty * 1.0))
            total_mv = sum(h[2] for h in holdings) or 1.0
            for (eid, qty, mv) in holdings:
                weight = mv / total_mv
                px_used = price_lookup.get((eid, dstr), 0.0)
                pos_rows.append((
                    eid, pf["id"], dstr, pf["source"],
                    round(qty, 2), round(mv, 2), round(mv * 0.95, 2), 0.0,
                    round(weight, 6), round(px_used, 4), pf["ccy"], None, None,
                ))
    cur.executemany(
        """INSERT INTO fact_positions
           (entity_id, portfolio_id, reference_date, source, quantity, market_value,
            cost_basis, accrued_interest, weight, price_used, currency, yield_to_maturity, duration)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        pos_rows,
    )

    counts = {
        "dim_entity": cur.execute("SELECT COUNT(*) FROM dim_entity").fetchone()[0],
        "dim_entity_identifiers": cur.execute("SELECT COUNT(*) FROM dim_entity_identifiers").fetchone()[0],
        "dim_portfolio": cur.execute("SELECT COUNT(*) FROM dim_portfolio").fetchone()[0],
        "fact_prices": cur.execute("SELECT COUNT(*) FROM fact_prices").fetchone()[0],
        "fact_positions": cur.execute("SELECT COUNT(*) FROM fact_positions").fetchone()[0],
    }
    logger.info(f"seeded reference DB: {counts}")
    return counts
