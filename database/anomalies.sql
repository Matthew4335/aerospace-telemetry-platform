
CREATE TABLE IF NOT EXISTS telemetry_anomalies (
    anomaly_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    reading_id BIGINT NOT NULL UNIQUE
        REFERENCES telemetry_readings(reading_id)
        ON DELETE CASCADE,

    anomaly_score DOUBLE PRECISION NOT NULL,

    model_version VARCHAR(50) NOT NULL
        DEFAULT 'isolation_forest_v1',

    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_anomalies_model
    ON telemetry_anomalies(model_version);
