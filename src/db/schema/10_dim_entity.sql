-- src/db/schema/10_dim_entity.sql
-- ---------------------------------------------------------------------------
-- dim_entity : security / instrument master. One row per held thing.
-- ---------------------------------------------------------------------------
-- Grain          : one row per entity_id (a security, fund, ETF, or cash unit)
-- Conventions     : entity_id (NOT security_id) to align with fact_prices /
--                   fact_positions. asset_class drives positioning + contribution
--                   grouping. Synthetic cash entities use asset_class='cash'.
-- NOTE            : This is a REFERENCE table for front-end development only.
--                   The authoritative dim_entity lives on the ETL machine.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_entity (
    entity_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name   TEXT NOT NULL,
    asset_class    TEXT NOT NULL,              -- equity | bond | cash | fund
    sector         TEXT,                       -- GICS-ish bucket, NULL for cash
    isin           TEXT,                       -- NULL for synthetic cash
    ticker         TEXT,
    base_currency  TEXT NOT NULL,
    country        TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_dim_entity_asset_class ON dim_entity (asset_class);
CREATE INDEX IF NOT EXISTS ix_dim_entity_isin        ON dim_entity (isin);
