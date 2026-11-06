-- Query 1: Count valid readings by sensor

SELECT
    s.sensor_name,
    s.sensor_type,
    s.measurement_unit,
    COUNT(*) AS total_readings
FROM telemetry_readings t
JOIN sensors s
    ON t.sensor_id = s.sensor_id
JOIN missions m
    ON t.mission_id = m.mission_id
JOIN vehicles v
    ON m.vehicle_id = v.vehicle_id
WHERE m.mission_name = 'Test Flight 001'
  AND v.vehicle_name = 'GTXR Test Vehicle 01'
GROUP BY s.sensor_id
ORDER BY s.sensor_name;

-- Query 2: Sensor summary statistics

SELECT
    s.sensor_name,
    COUNT(*) AS sample_count,
    ROUND(MIN(t.measurement_value)::NUMERIC, 2) AS min_value,
    ROUND(MAX(t.measurement_value)::NUMERIC, 2) AS max_value,
    ROUND(AVG(t.measurement_value)::NUMERIC, 2) AS avg_value,
    ROUND(STDDEV_SAMP(t.measurement_value)::NUMERIC, 2)
        AS std_deviation,
    s.measurement_unit
FROM telemetry_readings t
JOIN sensors s
    ON t.sensor_id = s.sensor_id
JOIN missions m
    ON t.mission_id = m.mission_id
JOIN vehicles v
    ON m.vehicle_id = v.vehicle_id
WHERE m.mission_name = 'Test Flight 001'
    AND v.vehicle_name = 'GTXR Test Vehicle 01'
GROUP BY
    s.sensor_id
ORDER BY s.sensor_name;

-- Query 3: Highest recorded altitude

SELECT
    m.mission_name,
    t.recorded_at,
    t.measurement_value AS altitude_meters
FROM telemetry_readings t
JOIN missions m
    ON t.mission_id = m.mission_id
JOIN sensors s
    ON t.sensor_id = s.sensor_id
JOIN vehicles v
    ON m.vehicle_id = v.vehicle_id
WHERE m.mission_name = 'Test Flight 001'
    AND s.sensor_name = 'ALT-01'
    AND v.vehicle_name = 'GTXR Test Vehicle 01'
ORDER BY
    t.measurement_value DESC,
    t.recorded_at ASC
LIMIT 1;

-- Query 4: Average altitude per 10-second interval

SELECT
    date_bin(
        INTERVAL '10 seconds',
        t.recorded_at,
        m.launch_time
    ) AS time_bucket,

    ROUND(
        AVG(t.measurement_value)::NUMERIC,
        2
    ) AS avg_altitude_meters,

    COUNT(*) AS sample_count

FROM telemetry_readings t
JOIN sensors s
    ON t.sensor_id = s.sensor_id
JOIN missions m
    ON t.mission_id = m.mission_id
JOIN vehicles v
    ON m.vehicle_id = v.vehicle_id

WHERE m.mission_name = 'Test Flight 001'
  AND s.sensor_name = 'ALT-01'
  AND v.vehicle_name = 'GTXR Test Vehicle 01'

GROUP BY
    date_bin(
        INTERVAL '10 seconds',
        t.recorded_at,
        m.launch_time
    )

ORDER BY time_bucket;

-- Query 7: Altitude changes between consecutive readings

WITH altitude_history AS (
    SELECT
        t.recorded_at,
        t.measurement_value AS altitude,

        LAG(t.measurement_value) OVER (
            PARTITION BY t.mission_id, t.sensor_id
            ORDER BY t.recorded_at
        ) AS previous_altitude

    FROM telemetry_readings t
    JOIN sensors s
        ON t.sensor_id = s.sensor_id
    JOIN missions m
        ON t.mission_id = m.mission_id
    JOIN vehicles v
        ON m.vehicle_id = v.vehicle_id

    WHERE m.mission_name = 'Test Flight 001'
      AND s.sensor_name = 'ALT-01'
      AND v.vehicle_name = 'GTXR Test Vehicle 01'
)

SELECT
    recorded_at,
    ROUND(altitude::NUMERIC, 2) AS altitude,
    ROUND(previous_altitude::NUMERIC, 2)
        AS previous_altitude,

    ROUND(
        (altitude - previous_altitude)::NUMERIC,
        2
    ) AS altitude_change

FROM altitude_history
ORDER BY recorded_at
LIMIT 30;