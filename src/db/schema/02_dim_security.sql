-- 02_dim_security.sql
-- Domain-specific attributes for entity_type='security'/'fund'. SCD Type 1.
-- Identifiers (isin/parsekyable/...) live in dim_entity_identifiers, not here.
CREATE TABLE IF NOT EXISTS dim_security (
    security_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id     INTEGER NOT NULL UNIQUE REFERENCES dim_entity (entity_id),
    ticker        TEXT,
    name          TEXT,
    short_name    TEXT,
    security_name TEXT,
    sec_num_des   TEXT,
    currency      TEXT,
    country       TEXT,
    exchange      TEXT,
    market_sector TEXT,
    security_type TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
