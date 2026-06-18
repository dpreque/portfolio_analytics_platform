-- 23_fact_positions.sql
-- Daily holdings, multi-source ready. One row per holding per portfolio per day
-- per source. Cash positions point security_entity_id at synthetic per-currency
-- dim_entity rows (entity_type='cash'). weight is 0..1, MV-based, per (portfolio_id, date).
-- date column (coherent with fact_prices + staging). DOUBLE PRECISION facts.
CREATE TABLE IF NOT EXISTS fact_positions (
    portfolio_id       INTEGER NOT NULL,
    security_entity_id INTEGER NOT NULL,
    date               DATE NOT NULL,
    source             TEXT NOT NULL,          -- fms | sbs | bloomberg | scraper
    quantity           DOUBLE PRECISION,
    market_value       DOUBLE PRECISION,
    cost_basis         DOUBLE PRECISION,
    accrued_interest   DOUBLE PRECISION,
    weight             DOUBLE PRECISION,       -- 0..1, portfolio weight by MV
    price_used         DOUBLE PRECISION,
    currency           TEXT,
    yield_to_maturity  DOUBLE PRECISION,
    duration           DOUBLE PRECISION,
    loaded_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (portfolio_id, security_entity_id, date, source),
    FOREIGN KEY (portfolio_id)       REFERENCES dim_portfolio (portfolio_id),
    FOREIGN KEY (security_entity_id) REFERENCES dim_entity (entity_id)
);
CREATE INDEX IF NOT EXISTS idx_fact_positions_date    ON fact_positions (date);
CREATE INDEX IF NOT EXISTS idx_fact_positions_pf_date ON fact_positions (portfolio_id, date);
CREATE INDEX IF NOT EXISTS idx_fact_positions_sec     ON fact_positions (security_entity_id);
CREATE INDEX IF NOT EXISTS idx_fact_positions_source  ON fact_positions (source);
