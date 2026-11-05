
import math
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REJECTED_DIR = PROJECT_ROOT / "data" / "rejected"

load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")


# --------------------------------------------------
# 2. Read source files
# --------------------------------------------------

def read_source_files():
    vehicles = pd.read_csv(RAW_DIR / "vehicles.csv")
    missions = pd.read_csv(RAW_DIR / "missions.csv")
    sensors = pd.read_csv(RAW_DIR / "sensors.csv")
    readings = pd.read_csv(RAW_DIR / "telemetry_readings.csv")

    # Convert values without crashing on bad data.
    readings["parsed_time"] = pd.to_datetime(
        readings["recorded_at"],
        errors="coerce",
        utc=True,
        format="ISO8601",
    )

    readings["parsed_value"] = pd.to_numeric(
        readings["measurement_value"],
        errors="coerce",
    )

    return vehicles, missions, sensors, readings


# --------------------------------------------------
# 3. Load reference data
# --------------------------------------------------

def load_metadata(conn, vehicles, missions, sensors):

    for vehicle in vehicles.to_dict("records"):
        conn.execute(
            text("""
                INSERT INTO vehicles (
                    vehicle_name, vehicle_type, manufacturer
                )
                VALUES (
                    :vehicle_name, :vehicle_type, :manufacturer
                )
                ON CONFLICT (vehicle_name) DO NOTHING
            """),
            vehicle,
        )

    for mission in missions.to_dict("records"):
        conn.execute(
            text("""
                INSERT INTO missions (
                    vehicle_id,
                    mission_name,
                    launch_time,
                    landing_time,
                    status
                )
                SELECT
                    v.vehicle_id,
                    :mission_name,
                    :launch_time,
                    :landing_time,
                    :status
                FROM vehicles v
                WHERE v.vehicle_name = :vehicle_name
                ON CONFLICT (mission_name) DO NOTHING
            """),
            mission,
        )

    for sensor in sensors.to_dict("records"):
        conn.execute(
            text("""
                INSERT INTO sensors (
                    vehicle_id,
                    sensor_name,
                    sensor_type,
                    measurement_unit
                )
                SELECT
                    v.vehicle_id,
                    :sensor_name,
                    :sensor_type,
                    :measurement_unit
                FROM vehicles v
                WHERE v.vehicle_name = :vehicle_name
                ON CONFLICT (vehicle_id, sensor_name) DO NOTHING
            """),
            sensor,
        )


# --------------------------------------------------
# 4. Build foreign-key lookup dictionaries
# --------------------------------------------------

def get_lookup_tables(conn):

    mission_rows = conn.execute(
        text("""
            SELECT
                m.mission_id,
                m.mission_name,
                m.vehicle_id,
                v.vehicle_name
            FROM missions m
            JOIN vehicles v
                ON m.vehicle_id = v.vehicle_id
        """)
    ).mappings().all()

    sensor_rows = conn.execute(
        text("""
            SELECT sensor_id, vehicle_id, sensor_name
            FROM sensors
        """)
    ).mappings().all()

    missions = {
        row["mission_name"]: dict(row)
        for row in mission_rows
    }

    sensors = {
        (row["vehicle_id"], row["sensor_name"]):
            row["sensor_id"]
        for row in sensor_rows
    }

    return missions, sensors


# --------------------------------------------------
# 5. Validate and transform telemetry
# --------------------------------------------------

def transform_readings(readings, missions, sensors):

    valid_rows = []
    rejected_rows = []

    seen_keys = set()

    for row in readings.itertuples(index=False):

        reason = None
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
            sensor_id = sensors.get(
                (
                    mission["vehicle_id"],
                    row.sensor_name,
                )
            )

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


# --------------------------------------------------
# 6. Insert validated readings
# --------------------------------------------------

def insert_telemetry(conn, valid_rows):

    if not valid_rows:
        return

    insert_statement = text("""
        INSERT INTO telemetry_readings (
            mission_id,
            sensor_id,
            recorded_at,
            measurement_value
        )
        VALUES (
            :mission_id,
            :sensor_id,
            :recorded_at,
            :measurement_value
        )
        ON CONFLICT (
            mission_id, sensor_id, recorded_at
        ) DO NOTHING
    """)

    # Insert multiple records per database operation.
    batch_size = 1000

    for start in range(0, len(valid_rows), batch_size):
        batch = valid_rows[start:start + batch_size]

        conn.execute(insert_statement, batch)


# --------------------------------------------------
# 7. Run the complete pipeline
# --------------------------------------------------

def main():

    vehicles, missions_df, sensors_df, readings = (
        read_source_files()
    )

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

    # All database writes are in one transaction.
    with engine.begin() as conn:

        load_metadata(
            conn,
            vehicles,
            missions_df,
            sensors_df,
        )

        mission_lookup, sensor_lookup = (
            get_lookup_tables(conn)
        )

        # Verify existing mission records have the
        # expected vehicle before loading telemetry.
        for mission in missions_df.to_dict("records"):
            stored = mission_lookup.get(mission["mission_name"])

            if stored is None:
                raise ValueError(
                    f"Mission not found: {mission['mission_name']}"
                )

            if stored["vehicle_name"] != mission["vehicle_name"]:
                raise ValueError(
                    "Mission vehicle mismatch for "
                    + mission["mission_name"]
                )

        valid_rows, rejected_rows = transform_readings(
            readings,
            mission_lookup,
            sensor_lookup,
        )

        count_before = conn.execute(
            text("SELECT COUNT(*) FROM telemetry_readings")
        ).scalar_one()

        insert_telemetry(conn, valid_rows)

        count_after = conn.execute(
            text("SELECT COUNT(*) FROM telemetry_readings")
        ).scalar_one()

        inserted = count_after - count_before

    # Transaction has committed successfully here.
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    rejected_path = REJECTED_DIR / "rejected_readings.csv"

    pd.DataFrame(
        rejected_rows,
        columns=[
            "source_row_id",
            "mission_name",
            "sensor_name",
            "recorded_at",
            "measurement_value",
            "rejection_reason",
        ],
    ).to_csv(rejected_path, index=False)

    print("\nETL completed successfully!")
    print(f"Source records: {len(readings):,}")
    print(f"Valid source records: {len(valid_rows):,}")
    print(f"Rejected records: {len(rejected_rows):,}")
    print(f"New database rows: {inserted:,}")
    print(f"Previously existing/skipped: {len(valid_rows) - inserted:,}")
    print(f"Rejection report: {rejected_path}")

    if rejected_rows:
        reasons = pd.Series(
            [row["rejection_reason"] for row in rejected_rows]
        )
        print("\nRejections by reason:")
        print(reasons.value_counts().to_string())

    engine.dispose()


if __name__ == "__main__":
    main()
