-- src/db/schema/11_dim_entity_identifiers.sql
-- ---------------------------------------------------------------------------
-- dim_entity_identifiers : multi-identifier lookup for a security.
-- ---------------------------------------------------------------------------
-- Grain          : one row per (id_type, id_value)
-- id_type values  : isin | bloomberg_ticker | fms_instrument_id | currency_cash
--                   (fms_instrument_id is the FMS-internal code; NOT 'codigo_fms')
-- Purpose         : identity resolution. Used by the ETL when mapping FMS rows;
--                   exposed here so the front end can show source attribution.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_entity_identifiers (
    identifier_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id      INTEGER NOT NULL REFERENCES dim_entity (entity_id),
    id_type        TEXT NOT NULL,
    id_value       TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (id_type, id_value)
);

CREATE INDEX IF NOT EXISTS ix_entity_identifiers_entity ON dim_entity_identifiers (entity_id);
