-- 13_dim_entity_identifiers.sql
-- Maps internal entity_id to all vendor-specific identifiers.
-- One row per (entity_id, id_type, source).
CREATE TABLE IF NOT EXISTS dim_entity_identifiers (
    entity_id  INTEGER NOT NULL REFERENCES dim_entity (entity_id),
    id_type    TEXT NOT NULL,   -- parsekyable / isin / cusip / sedol / sbs
    id_value   TEXT NOT NULL,
    source     TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_id, id_type, source)
);
CREATE INDEX IF NOT EXISTS idx_entity_identifiers_value  ON dim_entity_identifiers (id_type, id_value);
CREATE INDEX IF NOT EXISTS idx_entity_identifiers_entity ON dim_entity_identifiers (entity_id);
