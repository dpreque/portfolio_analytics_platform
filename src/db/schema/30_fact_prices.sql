-- src/db/schema/30_fact_prices.sql
-- ---------------------------------------------------------------------------
-- fact_prices : daily prices, one value per (security, source, date).
-- ---------------------------------------------------------------------------
-- Grain          : (entity_id, source, reference_date)
-- source          : fms | sbs | bloomberg | scraper
-- Conventions     : entity_id (NOT security_id), reference_date (NOT as_of_date).
--                   Real ETL inserts ON CONFLICT DO NOTHING (prices are not
--                   restated, unlike positions). Multiple sources per security
--                   per day is the whole point of the price-viewer dashboard.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_prices (
    entity_id       INTEGER NOT NULL REFERENCES dim_entity (entity_id),
    source          TEXT NOT NULL,
    reference_date  TEXT NOT NULL,             -- ISO date 'YYYY-MM-DD'
    price           REAL NOT NULL,
    currency        TEXT,
    price_type      TEXT NOT NULL DEFAULT 'close',
    loaded_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (entity_id, source, reference_date)
);

CREATE INDEX IF NOT EXISTS ix_fact_prices_entity_date
    ON fact_prices (entity_id, reference_date);
