-- src/db/schema/22_fact_positions.sql
-- ---------------------------------------------------------------------------
-- fact_positions : daily holdings, multi-source ready.
-- ---------------------------------------------------------------------------
-- Grain          : (entity_id, portfolio_id, reference_date, source)
-- entity_id       : the held security (FK dim_entity)
-- portfolio_id    : the holder        (FK dim_portfolio)
-- weight          : 0..1, MV-based, computed per (portfolio_id, reference_date)
-- Conventions     : entity_id + reference_date match fact_prices. reference_date
--                   kept as TEXT (ISO 'YYYY-MM-DD') so string params compare and
--                   sort directly, mirroring the prior reference layer.
-- Dialect         : PostgreSQL (psycopg v3).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_positions (
    entity_id          INTEGER NOT NULL REFERENCES dim_entity (entity_id),
    portfolio_id       INTEGER NOT NULL REFERENCES dim_portfolio (portfolio_id),
    reference_date     TEXT NOT NULL,                  -- ISO date 'YYYY-MM-DD'
    source             TEXT NOT NULL,                  -- fms | sbs | bloomberg | scraper
    quantity           DOUBLE PRECISION,
    market_value       DOUBLE PRECISION,
    cost_basis         DOUBLE PRECISION,
    accrued_interest   DOUBLE PRECISION,
    weight             DOUBLE PRECISION,               -- 0..1, MV-based
    price_used         DOUBLE PRECISION,
    currency           TEXT,
    yield_to_maturity  DOUBLE PRECISION,
    duration           DOUBLE PRECISION,
    loaded_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_id, portfolio_id, reference_date, source)
);

CREATE INDEX IF NOT EXISTS ix_fact_positions_portfolio_date
    ON fact_positions (portfolio_id, reference_date);
