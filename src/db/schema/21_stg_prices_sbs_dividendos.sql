-- 21_stg_prices_sbs_dividendos.sql
-- Staging for SBS daily dividends file (dividendos). FK-free landing zone.
CREATE TABLE IF NOT EXISTS stg_prices_sbs_dividendos (
    fecha_vector  DATE,
    codigo_sbs    TEXT NOT NULL,
    isin          TEXT,
    nemonico      TEXT,
    emisor        TEXT,
    moneda        TEXT,
    factor_ajuste DOUBLE PRECISION,
    tipo_entrega  TEXT,
    date          DATE NOT NULL,
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (codigo_sbs, date, loaded_at)
);
CREATE INDEX IF NOT EXISTS idx_stg_sbs_dividendos_date ON stg_prices_sbs_dividendos (date);
CREATE INDEX IF NOT EXISTS idx_stg_sbs_dividendos_isin ON stg_prices_sbs_dividendos (isin);
