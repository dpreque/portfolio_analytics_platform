-- src/db/schema/24_fact_contribution.sql
-- ---------------------------------------------------------------------------
-- fact_contribution : precomputed per-holding contribution to portfolio return.
-- ---------------------------------------------------------------------------
-- FORWARD-LOOKING. Created empty. Today the Contribution dashboard derives these
-- numbers on the fly from fact_positions x fact_prices (DerivedContributionProvider).
-- Once an ETL job populates THIS table, FactContributionProvider reads it instead
-- -- no front-end change, no route change.
--
-- Grain          : (portfolio_id, entity_id, period_start, period_end, source)
-- period_return   : holding return over [period_start, period_end]
-- contribution    : weight_at_start * period_return  (sums to portfolio return)
-- Dialect         : PostgreSQL (psycopg v3).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_contribution (
    portfolio_id    INTEGER NOT NULL REFERENCES dim_portfolio (portfolio_id),
    entity_id       INTEGER NOT NULL REFERENCES dim_entity (entity_id),
    period_start    TEXT NOT NULL,                  -- ISO date 'YYYY-MM-DD'
    period_end      TEXT NOT NULL,                  -- ISO date 'YYYY-MM-DD'
    source          TEXT NOT NULL,                  -- fms | sbs | bloomberg | scraper
    weight          DOUBLE PRECISION,               -- beginning-of-period weight, 0..1
    period_return   DOUBLE PRECISION,               -- holding return over the period
    contribution    DOUBLE PRECISION,               -- weight * period_return
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (portfolio_id, entity_id, period_start, period_end, source)
);

CREATE INDEX IF NOT EXISTS ix_fact_contribution_pf_period
    ON fact_contribution (portfolio_id, period_start, period_end);
