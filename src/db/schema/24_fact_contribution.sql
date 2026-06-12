-- src/db/schema/24_fact_contribution.sql
-- ---------------------------------------------------------------------------
-- fact_contribution : precomputed per-holding contribution to portfolio return.
-- ---------------------------------------------------------------------------
-- FORWARD-LOOKING. Created empty in the reference DB. Today the Contribution
-- dashboard derives these numbers on the fly from fact_positions x fact_prices
-- (see DerivedContributionProvider). Once an ETL job populates THIS table, the
-- API's FactContributionProvider reads it instead -- no front-end change, no
-- route change (see web/api/services/contribution_providers.py).
--
-- Grain          : (portfolio_id, entity_id, period_start, period_end, source)
-- period_return   : holding return over [period_start, period_end]
-- contribution    : weight_at_start * period_return  (sums to portfolio return)
-- Conventions     : entity_id / portfolio_id / *_date naming matches the rest of
--                   the schema. Designed so a real attribution engine (e.g.
--                   Brinson, multi-period geometric linking) can populate it
--                   without changing the read API's response shape.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_contribution (
    portfolio_id    INTEGER NOT NULL REFERENCES dim_portfolio (portfolio_id),
    entity_id       INTEGER NOT NULL REFERENCES dim_entity (entity_id),
    period_start    TEXT NOT NULL,                  -- ISO date 'YYYY-MM-DD'
    period_end      TEXT NOT NULL,                  -- ISO date 'YYYY-MM-DD'
    source          TEXT NOT NULL,                  -- fms | sbs | bloomberg | scraper
    weight          REAL,                           -- beginning-of-period weight, 0..1
    period_return   REAL,                           -- holding return over the period
    contribution    REAL,                           -- weight * period_return
    loaded_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (portfolio_id, entity_id, period_start, period_end, source)
);

CREATE INDEX IF NOT EXISTS ix_fact_contribution_pf_period
    ON fact_contribution (portfolio_id, period_start, period_end);
