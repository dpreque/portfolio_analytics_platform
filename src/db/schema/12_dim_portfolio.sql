-- src/db/schema/12_dim_portfolio.sql
-- ---------------------------------------------------------------------------
-- dim_portfolio : portfolio master. One row per (internal_code, source).
-- ---------------------------------------------------------------------------
-- portfolio_type  : own_account | regulator_filing | etf
-- status          : backfill-pending | active | suspended | inactive | error-hold
-- parent_entity_id: ETFs link back to their dim_entity row here
-- Dialect         : PostgreSQL (psycopg v3). Numbered 12 (was 27) so this
--                   dimension is created BEFORE the fact tables that FK to it
--                   (Postgres requires the referenced table to exist already).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_portfolio (
    portfolio_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    internal_code    TEXT NOT NULL,
    source           TEXT NOT NULL,             -- fms | sbs | bloomberg | scraper
    portfolio_type   TEXT NOT NULL,             -- own_account | regulator_filing | etf
    display_name     TEXT,
    base_currency    TEXT,
    parent_entity_id INTEGER REFERENCES dim_entity (entity_id),
    status           TEXT NOT NULL,             -- lifecycle, see header
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (internal_code, source)
);
