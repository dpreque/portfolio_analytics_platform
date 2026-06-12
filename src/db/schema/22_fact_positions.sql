-- src/db/schema/22_fact_positions.sql
-- ---------------------------------------------------------------------------
-- fact_positions : daily holdings, multi-source ready.
-- ---------------------------------------------------------------------------
-- Grain          : (entity_id, portfolio_id, reference_date, source)
-- entity_id       : the held security (FK dim_entity)
-- portfolio_id    : the holder        (FK dim_portfolio)
-- weight          : 0..1, MV-based, computed per (portfolio_id, reference_date)
-- Conventions     : entity_id + reference_date match fact_prices (NOT
--                   security_id / as_of_date). Real ETL upserts ON CONFLICT
--                   DO UPDATE (positions get restated), unlike fact_prices.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_positions (
    entity_id          INTEGER NOT NULL REFERENCES dim_entity (entity_id),
    portfolio_id       INTEGER NOT NULL REFERENCES dim_portfolio (portfolio_id),
    reference_date     TEXT NOT NULL,                  -- ISO date 'YYYY-MM-DD'
    source             TEXT NOT NULL,                  -- fms | sbs | bloomberg | scraper
    quantity           REAL,
    market_value       REAL,
    cost_basis         REAL,
    accrued_interest   REAL,
    weight             REAL,                           -- 0..1, MV-based
    price_used         REAL,
    currency           TEXT,
    yield_to_maturity  REAL,
    duration           REAL,
    loaded_at          TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (entity_id, portfolio_id, reference_date, source)
);

CREATE INDEX IF NOT EXISTS ix_fact_positions_portfolio_date
    ON fact_positions (portfolio_id, reference_date);
