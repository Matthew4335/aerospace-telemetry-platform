
import math

import pandas as pd


def transform_readings(readings, missions, sensors):
    """
    Validate telemetry and prepare records for PostgreSQL.

    missions: dictionary keyed by mission name
    sensors: dictionary keyed by (vehicle_id, sensor_name)

    Returns:
        valid_rows: list of database-ready dictionaries
        rejected_rows: list of rejected source records
    """

    df = readings.copy()

    # Convert source timestamps to UTC.
    df["parsed_time"] = pd.to_datetime(
        df["recorded_at"],
        errors="coerce",
        utc=True,
        format="ISO8601",
    )

    # Convert measurements to numeric values.
    df["parsed_value"] = pd.to_numeric(
        df["measurement_value"],
        errors="coerce",
    )

    valid_rows = []
    rejected_rows = []

    # Track duplicates within this CSV.
    seen_keys = set()

    for row in df.itertuples(index=False):
        reason = None

        # Look up the mission using its name.
        mission = missions.get(row.mission_name)

        if mission is None:
            reason = "unknown_mission"

        elif pd.isna(row.parsed_time):
            reason = "invalid_timestamp"

        elif pd.isna(row.parsed_value):
            reason = "missing_or_invalid_measurement"

        elif not math.isfinite(float(row.parsed_value)):
            reason = "non_finite_measurement"

        else:
            # Sensors belong to a specific vehicle.
            sensor_key = (
                mission["vehicle_id"],
                row.sensor_name,
            )

            sensor_id = sensors.get(sensor_key)

            if sensor_id is None:
                reason = "unknown_sensor"

            else:
                timestamp = row.parsed_time.to_pydatetime()

                unique_key = (
                    mission["mission_id"],
                    sensor_id,
                    timestamp,
                )

                if unique_key in seen_keys:
                    reason = "duplicate_sensor_timestamp"

                else:
                    seen_keys.add(unique_key)

                    valid_rows.append({
                        "mission_id": mission["mission_id"],
                        "sensor_id": sensor_id,
                        "recorded_at": timestamp,
                        "measurement_value": float(
                            row.parsed_value
                        ),
                    })

        # Preserve rejected source records and their reasons.
        if reason is not None:
            rejected_rows.append({
                "source_row_id": row.source_row_id,
                "mission_name": row.mission_name,
                "sensor_name": row.sensor_name,
                "recorded_at": row.recorded_at,
                "measurement_value": row.measurement_value,
                "rejection_reason": reason,
            })

    return valid_rows, rejected_rows
