-- Aerospace Telemetry Data Engineering Platform
-- PostgreSQL database schema

-- 1. VEHICLES
-- Stores information about individual rockets.

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_name VARCHAR(100) NOT NULL UNIQUE,
    vehicle_type VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 2. MISSIONS
-- Each mission is associated with one vehicle.

CREATE TABLE IF NOT EXISTS missions (
    mission_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(vehicle_id),
    mission_name VARCHAR(100) NOT NULL UNIQUE,
    launch_time TIMESTAMPTZ NOT NULL,
    landing_time TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'planned',

    CONSTRAINT valid_mission_status
        CHECK (status IN ('planned', 'active', 'completed', 'aborted')),

    CONSTRAINT valid_mission_times
        CHECK (landing_time IS NULL OR landing_time >= launch_time)
);


-- 3. SENSORS
-- Each sensor belongs to a particular vehicle.

CREATE TABLE IF NOT EXISTS sensors (
    sensor_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(vehicle_id),
    sensor_name VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    measurement_unit VARCHAR(20) NOT NULL,

    CONSTRAINT unique_vehicle_sensor
        UNIQUE (vehicle_id, sensor_name)
);


-- 4. TELEMETRY READINGS
-- Stores individual timestamped sensor measurements.

CREATE TABLE IF NOT EXISTS telemetry_readings (
    reading_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mission_id INTEGER NOT NULL REFERENCES missions(mission_id),
    sensor_id INTEGER NOT NULL REFERENCES sensors(sensor_id),
    recorded_at TIMESTAMPTZ NOT NULL,
    measurement_value DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_sensor_reading
        UNIQUE (mission_id, sensor_id, recorded_at),

    CONSTRAINT valid_measurement_value
    CHECK (
        measurement_value NOT IN (
            'Infinity'::DOUBLE PRECISION,
            '-Infinity'::DOUBLE PRECISION,
            'NaN'::DOUBLE PRECISION
        )
    )
);


-- 5. ANOMALY EVENTS
-- Records unusual readings identified by detection rules or ML.

CREATE TABLE IF NOT EXISTS anomaly_events (
    anomaly_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reading_id BIGINT NOT NULL
        REFERENCES telemetry_readings(reading_id),
    detection_method VARCHAR(50) NOT NULL,
    anomaly_score DOUBLE PRECISION,
    description TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_anomaly_score
    CHECK (
        anomaly_score IS NULL
        OR anomaly_score NOT IN (
            'Infinity'::DOUBLE PRECISION,
            '-Infinity'::DOUBLE PRECISION,
            'NaN'::DOUBLE PRECISION
        )
    ),

    CONSTRAINT unique_reading_detection
        UNIQUE (reading_id, detection_method)
);