-- 17_stg_prices_sbs_vector_completo.sql
-- Staging for SBS daily general prices file (vector_completo). FK-free landing zone.
CREATE TABLE IF NOT EXISTS stg_prices_sbs_vector_completo (
    codigo_sbs       TEXT NOT NULL,
    isin             TEXT,
    nemonico         TEXT,
    tipo_instrumento TEXT,
    emisor           TEXT,
    moneda           TEXT,
    precio           DOUBLE PRECISION,
    variacion        DOUBLE PRECISION,
    date             DATE NOT NULL,
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (codigo_sbs, date, loaded_at)
);
CREATE INDEX IF NOT EXISTS idx_stg_sbs_vector_completo_date ON stg_prices_sbs_vector_completo (date);
CREATE INDEX IF NOT EXISTS idx_stg_sbs_vector_completo_isin ON stg_prices_sbs_vector_completo (isin);
