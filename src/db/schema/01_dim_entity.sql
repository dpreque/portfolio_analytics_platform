-- 01_dim_entity.sql
-- Anchor table for all entities (securities, macro variables, funds, etc.).
-- One row per unique real-world entity regardless of domain.
-- NOTE: 'cash' is added to the entity_type CHECK so synthetic per-currency cash
-- entities (used by fact_positions) are allowed (resolves the documented
-- dim_entity/fact_positions cash inconsistency in this reference DB).
CREATE TABLE IF NOT EXISTS dim_entity (
    entity_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    procode     TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('security','macro','index','fund','cash')),
    name        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
