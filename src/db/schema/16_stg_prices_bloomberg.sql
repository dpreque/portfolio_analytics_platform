-- 16_stg_prices_bloomberg.sql
-- Raw price observations from Bloomberg API. Long format. FK-free landing zone.
CREATE TABLE IF NOT EXISTS stg_prices_bloomberg (
    stg_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parsekyable TEXT NOT NULL,
    field       TEXT NOT NULL,
    date        DATE NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (parsekyable, field, date, loaded_at)
);
CREATE INDEX IF NOT EXISTS idx_stg_prices_bloomberg_ticker ON stg_prices_bloomberg (parsekyable);
CREATE INDEX IF NOT EXISTS idx_stg_prices_bloomberg_date   ON stg_prices_bloomberg (date);
CREATE INDEX IF NOT EXISTS idx_stg_prices_bloomberg_loaded ON stg_prices_bloomberg (loaded_at);
