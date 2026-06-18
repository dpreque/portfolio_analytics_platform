-- 20_stg_prices_sbs_tipo_cambio.sql
-- Staging for SBS FX rates file (tipo_cambio). FK-free landing zone.
CREATE TABLE IF NOT EXISTS stg_prices_sbs_tipo_cambio (
    moneda_nocional    TEXT NOT NULL,
    moneda_contraparte TEXT NOT NULL,
    fuente             TEXT NOT NULL,
    bid_original       DOUBLE PRECISION,
    ask_original       DOUBLE PRECISION,
    pen_bid            DOUBLE PRECISION,
    pen_ask            DOUBLE PRECISION,
    var_bid            DOUBLE PRECISION,
    var_ask            DOUBLE PRECISION,
    date               DATE NOT NULL,
    loaded_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (moneda_nocional, moneda_contraparte, fuente, date, loaded_at)
);
CREATE INDEX IF NOT EXISTS idx_stg_sbs_tipo_cambio_date ON stg_prices_sbs_tipo_cambio (date);
CREATE INDEX IF NOT EXISTS idx_stg_sbs_tipo_cambio_pair ON stg_prices_sbs_tipo_cambio (moneda_nocional, moneda_contraparte);
