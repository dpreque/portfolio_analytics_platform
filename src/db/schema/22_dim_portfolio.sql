-- 22_dim_portfolio.sql
-- One row per (procode, source). A 'portfolio' is anything that holds positions:
-- own_account (FMS), regulator_filing (SBS), etf (Bloomberg/scraper).
-- parent_entity_id links ETF portfolios back to their dim_entity row.
CREATE TABLE IF NOT EXISTS dim_portfolio (
    portfolio_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    procode          TEXT NOT NULL,
    source           TEXT NOT NULL,            -- fms | sbs | bloomberg | scraper
    portfolio_type   TEXT NOT NULL,            -- own_account | regulator_filing | etf
    display_name     TEXT,
    base_currency    TEXT,
    parent_entity_id INTEGER,                  -- links ETFs back to dim_entity
    status           TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('backfill-pending','active','suspended','inactive','error_hold')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (procode, source),
    FOREIGN KEY (parent_entity_id) REFERENCES dim_entity (entity_id)
);
CREATE INDEX IF NOT EXISTS idx_dim_portfolio_source ON dim_portfolio (source);
CREATE INDEX IF NOT EXISTS idx_dim_portfolio_status ON dim_portfolio (status);
CREATE INDEX IF NOT EXISTS idx_dim_portfolio_parent ON dim_portfolio (parent_entity_id);
