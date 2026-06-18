-- 04_dim_security_fund.sql
-- Fund-specific extension of dim_security (1:1).
CREATE TABLE IF NOT EXISTS dim_security_fund (
    security_id INTEGER PRIMARY KEY REFERENCES dim_security (security_id),
    fund_type   TEXT,
    asset_class TEXT,
    geography   TEXT,
    objective   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
