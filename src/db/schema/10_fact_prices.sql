-- 10_fact_prices.sql
-- Daily price observations. Pure long format, one value per row.
-- Keyed by series_id (-> series_registry resolves entity + source + field).
-- No revisions expected -- upsert on (series_id, date) DO NOTHING.
CREATE TABLE IF NOT EXISTS fact_prices (
    series_id INTEGER NOT NULL REFERENCES series_registry (series_id),
    date      DATE NOT NULL,
    price     DOUBLE PRECISION NOT NULL,
    source    TEXT NOT NULL,
    PRIMARY KEY (series_id, date)
);
CREATE INDEX IF NOT EXISTS idx_fact_prices_date ON fact_prices (date);
