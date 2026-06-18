-- 03_dim_security_equity.sql
-- Equity-specific extension of dim_security (1:1).
CREATE TABLE IF NOT EXISTS dim_security_equity (
    security_id INTEGER PRIMARY KEY REFERENCES dim_security (security_id),
    sector      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
