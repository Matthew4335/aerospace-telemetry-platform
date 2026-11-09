
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from etl.load import (
    insert_telemetry,
    reject_conflicting_readings,
)
from etl.transform import transform_readings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@pytest.fixture
def database_url():
    """Read the PostgreSQL connection URL."""

    url = os.getenv("DATABASE_URL")

    if not url:
        pytest.skip("DATABASE_URL not configured")

    return url


@pytest.fixture
def db_conn(database_url):
    """
    Provide a real PostgreSQL connection.

    Roll back test changes afterward so production
    development data remains untouched.
    """

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            transaction = conn.begin()

            try:
                yield conn

            finally:
                if transaction.is_active:
                    transaction.rollback()

    finally:
        engine.dispose()


def create_test_metadata(conn):
    """Create an isolated test vehicle, mission, and sensor."""

    suffix = uuid4().hex[:12]

    vehicle_name = f"Day8 Test Vehicle {suffix}"
    mission_name = f"Day8 Test Mission {suffix}"

    vehicle_id = conn.execute(
        text("""
            INSERT INTO vehicles (
                vehicle_name,
                vehicle_type,
                manufacturer
            )
            VALUES (
                :name,
                'rocket',
                'Test Manufacturer'
            )
            RETURNING vehicle_id
        """),
        {"name": vehicle_name},
    ).scalar_one()

    mission_id = conn.execute(
        text("""
            INSERT INTO missions (
                vehicle_id,
                mission_name,
                launch_time,
                landing_time,
                status
            )
            VALUES (
                :vehicle_id,
                :mission_name,
                :launch_time,
                :landing_time,
                'completed'
            )
            RETURNING mission_id
        """),
        {
            "vehicle_id": vehicle_id,
            "mission_name": mission_name,
            "launch_time": datetime(
                2026, 11, 1, 12, 0,
                tzinfo=timezone.utc,
            ),
            "landing_time": datetime(
                2026, 11, 1, 12, 5,
                tzinfo=timezone.utc,
            ),
        },
    ).scalar_one()

    sensor_id = conn.execute(
        text("""
            INSERT INTO sensors (
                vehicle_id,
                sensor_name,
                sensor_type,
                measurement_unit
            )
            VALUES (
                :vehicle_id,
                'ALT-DAY8',
                'altitude',
                'm'
            )
            RETURNING sensor_id
        """),
        {"vehicle_id": vehicle_id},
    ).scalar_one()

    return {
        "vehicle_id": vehicle_id,
        "mission_id": mission_id,
        "sensor_id": sensor_id,
        "mission_name": mission_name,
    }


def make_readings(metadata):
    """Create two valid readings for a test mission."""

    return [
        {
            "mission_id": metadata["mission_id"],
            "sensor_id": metadata["sensor_id"],
            "recorded_at": datetime(
                2026, 11, 1, 12, 0, 1,
                tzinfo=timezone.utc,
            ),
            "measurement_value": 100.0,
        },
        {
            "mission_id": metadata["mission_id"],
            "sensor_id": metadata["sensor_id"],
            "recorded_at": datetime(
                2026, 11, 1, 12, 0, 2,
                tzinfo=timezone.utc,
            ),
            "measurement_value": 200.0,
        },
    ]


def test_running_same_load_twice(db_conn):
    """Second run must not create extra readings."""

    metadata = create_test_metadata(db_conn)
    readings = make_readings(metadata)

    reject_conflicting_readings(db_conn, readings)
    first_inserted = insert_telemetry(db_conn, readings)

    reject_conflicting_readings(db_conn, readings)
    second_inserted = insert_telemetry(db_conn, readings)

    count = db_conn.execute(
        text("""
            SELECT COUNT(*)
            FROM telemetry_readings
            WHERE mission_id = :mission_id
        """),
        {"mission_id": metadata["mission_id"]},
    ).scalar_one()

    assert first_inserted == 2
    assert second_inserted == 0
    assert count == 2


def test_conflicting_measurement_is_rejected(db_conn):
    """Existing measurements must not be overwritten."""

    metadata = create_test_metadata(db_conn)
    readings = make_readings(metadata)

    insert_telemetry(db_conn, readings)

    changed_reading = readings[0].copy()
    changed_reading["measurement_value"] = 999.0

    with pytest.raises(
        ValueError,
        match="Conflicting telemetry reading",
    ):
        reject_conflicting_readings(
            db_conn,
            [changed_reading],
        )

    stored_value = db_conn.execute(
        text("""
            SELECT measurement_value
            FROM telemetry_readings
            WHERE mission_id = :mission_id
              AND sensor_id = :sensor_id
              AND recorded_at = :recorded_at
        """),
        {
            "mission_id": metadata["mission_id"],
            "sensor_id": metadata["sensor_id"],
            "recorded_at": readings[0]["recorded_at"],
        },
    ).scalar_one()

    assert stored_value == 100.0


def test_duplicate_source_timestamp_is_rejected():
    """Transform should reject duplicate rows in a source CSV."""

    readings = pd.DataFrame([
        {
            "source_row_id": 1,
            "mission_name": "Test Flight 001",
            "sensor_name": "ALT-01",
            "recorded_at": "2026-11-01T12:00:01Z",
            "measurement_value": 100.0,
        },
        {
            "source_row_id": 2,
            "mission_name": "Test Flight 001",
            "sensor_name": "ALT-01",
            "recorded_at": "2026-11-01T12:00:01Z",
            "measurement_value": 150.0,
        },
    ])

    missions = {
        "Test Flight 001": {
            "mission_id": 1,
            "vehicle_id": 1,
        }
    }

    sensors = {
        (1, "ALT-01"): 10
    }

    valid, rejected = transform_readings(
        readings,
        missions,
        sensors,
    )

    assert len(valid) == 1
    assert len(rejected) == 1
    assert (
        rejected[0]["rejection_reason"]
        == "duplicate_sensor_timestamp"
    )


def test_database_enforces_foreign_keys(db_conn):
    """PostgreSQL must reject a nonexistent mission ID."""

    metadata = create_test_metadata(db_conn)

    with pytest.raises(IntegrityError):
        # Savepoint lets us recover from an expected SQL error.
        with db_conn.begin_nested():
            db_conn.execute(
                text("""
                    INSERT INTO telemetry_readings (
                        mission_id,
                        sensor_id,
                        recorded_at,
                        measurement_value
                    )
                    VALUES (
                        -999999,
                        :sensor_id,
                        :recorded_at,
                        100.0
                    )
                """),
                {
                    "sensor_id": metadata["sensor_id"],
                    "recorded_at": datetime(
                        2026, 11, 1, 12, 0, 1,
                        tzinfo=timezone.utc,
                    ),
                },
            )


def test_transaction_rolls_back_on_conflict(database_url):
    """A failed ETL transaction must not retain partial data."""

    engine = create_engine(database_url)
    mission_name = None

    try:
        with pytest.raises(
            ValueError,
            match="Conflicting telemetry reading",
        ):
            with engine.begin() as conn:
                metadata = create_test_metadata(conn)
                mission_name = metadata["mission_name"]

                readings = make_readings(metadata)

                # Insert records inside the transaction.
                insert_telemetry(conn, readings)

                # Deliberately create a conflicting value.
                changed = readings[0].copy()
                changed["measurement_value"] = 999.0

                reject_conflicting_readings(
                    conn,
                    [changed],
                )

        # The transaction should have rolled back.
        with engine.connect() as conn:
            remaining = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM missions
                    WHERE mission_name = :name
                """),
                {"name": mission_name},
            ).scalar_one()

        assert remaining == 0

    finally:
        engine.dispose()
