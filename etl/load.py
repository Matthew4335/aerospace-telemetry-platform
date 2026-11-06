
import pandas as pd
from sqlalchemy import text


BATCH_SIZE = 1000


def parse_timestamp(value):
    """Convert a CSV timestamp into a UTC datetime."""

    if pd.isna(value):
        return None

    timestamp = pd.to_datetime(value, utc=True)
    return timestamp.to_pydatetime()


def load_metadata(conn, vehicles, missions, sensors):
    """Insert vehicle, mission, and sensor metadata."""

    # 1. Vehicles
    for row in vehicles.to_dict("records"):
        manufacturer = row.get("manufacturer")

        if pd.isna(manufacturer):
            manufacturer = None

        conn.execute(
            text("""
                INSERT INTO vehicles (
                    vehicle_name,
                    vehicle_type,
                    manufacturer
                )
                VALUES (
                    :vehicle_name,
                    :vehicle_type,
                    :manufacturer
                )
                ON CONFLICT (vehicle_name) DO NOTHING
            """),
            {
                "vehicle_name": row["vehicle_name"],
                "vehicle_type": row["vehicle_type"],
                "manufacturer": manufacturer,
            },
        )

    # 2. Missions
    for row in missions.to_dict("records"):
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
            {
                "vehicle_name": row["vehicle_name"],
                "mission_name": row["mission_name"],
                "launch_time": parse_timestamp(
                    row["launch_time"]
                ),
                "landing_time": parse_timestamp(
                    row["landing_time"]
                ),
                "status": row["status"],
            },
        )

    # 3. Sensors
    for row in sensors.to_dict("records"):
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
                ON CONFLICT (
                    vehicle_id,
                    sensor_name
                ) DO NOTHING
            """),
            {
                "vehicle_name": row["vehicle_name"],
                "sensor_name": row["sensor_name"],
                "sensor_type": row["sensor_type"],
                "measurement_unit": row["measurement_unit"],
            },
        )


def get_lookup_tables(conn):
    """Get mission and sensor IDs from PostgreSQL."""

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
            SELECT
                sensor_id,
                vehicle_id,
                sensor_name
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


def insert_telemetry(conn, valid_rows):
    """Insert telemetry in batches of 1,000 rows."""

    if not valid_rows:
        return 0

    insert_query = text("""
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
            mission_id,
            sensor_id,
            recorded_at
        ) DO NOTHING
    """)

    inserted_count = 0

    for start in range(0, len(valid_rows), BATCH_SIZE):
        batch = valid_rows[start:start + BATCH_SIZE]

        result = conn.execute(insert_query, batch)

        if result.rowcount >= 0:
            inserted_count += result.rowcount

    return inserted_count
