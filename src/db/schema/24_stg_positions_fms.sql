-- 24_stg_positions_fms.sql
-- Raw landing for FMS sproc output. Permissive types, no FKs. batch-tagged.
CREATE TABLE IF NOT EXISTS stg_positions_fms (
    batch_id          TEXT NOT NULL,           -- e.g. 'fms_20260514_081532'
    loaded_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date              DATE,
    account_code      TEXT,                    -- FMS internal account id
    instrument_id     TEXT,                    -- FMS internal instrument id
    isin              TEXT,
    ticker            TEXT,
    description       TEXT,
    quantity          DOUBLE PRECISION,
    market_value      DOUBLE PRECISION,
    cost_basis        DOUBLE PRECISION,
    accrued_interest  DOUBLE PRECISION,
    currency          TEXT,
    price_used        DOUBLE PRECISION,
    yield_to_maturity DOUBLE PRECISION,
    duration          DOUBLE PRECISION,
    raw_payload       JSONB                    -- full sproc row, for audit
);
CREATE INDEX IF NOT EXISTS idx_stg_positions_fms_batch ON stg_positions_fms (batch_id);
CREATE INDEX IF NOT EXISTS idx_stg_positions_fms_date  ON stg_positions_fms (date);
