-- 19_stg_prices_sbs_rf_exterior.sql
-- Staging for SBS foreign fixed income file (rf_exterior). FK-free landing zone.
-- Note: no nemonico column (unlike sibling SBS staging) -- per source file.
CREATE TABLE IF NOT EXISTS stg_prices_sbs_rf_exterior (
    codigo_sbs             TEXT NOT NULL,
    isin                   TEXT,
    tipo_instrumento       TEXT,
    emisor                 TEXT,
    moneda                 TEXT,
    valor_facial           DOUBLE PRECISION,
    origen_precio          TEXT,
    fecha_emision          DATE,
    fecha_vencimiento      DATE,
    tasa_cupon             DOUBLE PRECISION,
    ultimo_cupon           DATE,
    proximo_cupon          DATE,
    precio_limpio_monto    DOUBLE PRECISION,
    precio_limpio_pct      DOUBLE PRECISION,
    precio_sucio_monto     DOUBLE PRECISION,
    precio_sucio_pct       DOUBLE PRECISION,
    interes_corrido_monto  DOUBLE PRECISION,
    variacion_precio_sucio DOUBLE PRECISION,
    date                   DATE NOT NULL,
    loaded_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (codigo_sbs, date, loaded_at)
);
CREATE INDEX IF NOT EXISTS idx_stg_sbs_rf_exterior_date ON stg_prices_sbs_rf_exterior (date);
CREATE INDEX IF NOT EXISTS idx_stg_sbs_rf_exterior_isin ON stg_prices_sbs_rf_exterior (isin);
