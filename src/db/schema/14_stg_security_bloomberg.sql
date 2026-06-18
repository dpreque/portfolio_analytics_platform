-- 14_stg_security_bloomberg.sql
-- Raw security attributes from Bloomberg API. Long format. FK-free landing zone.
CREATE TABLE IF NOT EXISTS stg_security_bloomberg (
    stg_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parsekyable TEXT NOT NULL,
    field       TEXT NOT NULL,
    value       TEXT,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (parsekyable, field, loaded_at)
);
CREATE INDEX IF NOT EXISTS idx_stg_security_bloomberg_ticker ON stg_security_bloomberg (parsekyable);
CREATE INDEX IF NOT EXISTS idx_stg_security_bloomberg_field  ON stg_security_bloomberg (field);
CREATE INDEX IF NOT EXISTS idx_stg_security_bloomberg_loaded ON stg_security_bloomberg (loaded_at);
