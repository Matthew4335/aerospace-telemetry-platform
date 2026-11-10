
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from api.main import app, get_db


@pytest.fixture
def client():
    """
    Create a disposable test database and API client.

    Real PostgreSQL telemetry is not modified.
    """

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create minimal tables for API testing.
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE vehicles (
                vehicle_id INTEGER PRIMARY KEY,
                vehicle_name TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE missions (
                mission_id INTEGER PRIMARY KEY,
                mission_name TEXT NOT NULL,
                vehicle_id INTEGER NOT NULL,
                launch_time TEXT NOT NULL,
                landing_time TEXT,
                status TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE sensors (
                sensor_id INTEGER PRIMARY KEY,
                sensor_name TEXT NOT NULL,
                measurement_unit TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE telemetry_readings (
                reading_id INTEGER PRIMARY KEY,
                mission_id INTEGER NOT NULL,
                sensor_id INTEGER NOT NULL,
                recorded_at TEXT NOT NULL,
                measurement_value REAL NOT NULL
            )
        """))

        # Add one test vehicle and mission.
        conn.execute(text("""
            INSERT INTO vehicles
            VALUES (1, 'Test Rocket')
        """))

        conn.execute(text("""
            INSERT INTO missions
            VALUES (
                1,
                'Test Flight',
                1,
                '2026-11-01T12:00:00+00:00',
                '2026-11-01T12:05:00+00:00',
                'completed'
            )
        """))

        # Add two test sensors.
        conn.execute(text("""
            INSERT INTO sensors
            VALUES (10, 'ALT-01', 'm')
        """))

        conn.execute(text("""
            INSERT INTO sensors
            VALUES (11, 'VEL-01', 'm/s')
        """))

        # Add three sample readings.
        conn.execute(text("""
            INSERT INTO telemetry_readings VALUES
                (
                    1, 1, 10,
                    '2026-11-01T12:00:01+00:00',
                    100.0
                ),
                (
                    2, 1, 10,
                    '2026-11-01T12:00:02+00:00',
                    150.0
                ),
                (
                    3, 1, 11,
                    '2026-11-01T12:00:02+00:00',
                    250.0
                )
        """))

    # Tell FastAPI to use the test database.
    def override_get_db():
        with engine.connect() as conn:
            yield conn

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client

    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_and_get_mission(client):
    response = client.get("/missions")

    assert response.status_code == 200
    assert len(response.json()) == 1

    assert (
        response.json()[0]["mission_name"]
        == "Test Flight"
    )

    detail = client.get("/missions/1")

    assert detail.status_code == 200
    assert (
        detail.json()["vehicle_name"]
        == "Test Rocket"
    )


def test_missing_mission(client):
    assert (
        client.get("/missions/999").status_code
        == 404
    )

    assert (
        client.get(
            "/missions/999/telemetry"
        ).status_code
        == 404
    )

    assert (
        client.get("/missions/999/stats").status_code
        == 404
    )


def test_telemetry_pagination(client):
    first = client.get(
        "/missions/1/telemetry?limit=2&offset=0"
    )

    second = client.get(
        "/missions/1/telemetry?limit=2&offset=2"
    )

    assert first.status_code == 200
    assert first.json()["total"] == 3
    assert len(first.json()["readings"]) == 2
    assert len(second.json()["readings"]) == 1

    ids = [
        row["reading_id"]
        for row in (
            first.json()["readings"]
            + second.json()["readings"]
        )
    ]

    assert ids == [1, 2, 3]


def test_sensor_filter(client):
    response = client.get(
        "/missions/1/telemetry?sensor_id=10"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2

    assert all(
        row["sensor_id"] == 10
        for row in response.json()["readings"]
    )


def test_stats(client):
    response = client.get("/missions/1/stats")

    assert response.status_code == 200

    data = response.json()

    assert data["total_readings"] == 3

    stats = {
        sensor["sensor_name"]: sensor
        for sensor in data["sensors"]
    }

    assert stats["ALT-01"]["reading_count"] == 2
    assert stats["ALT-01"]["minimum"] == 100.0
    assert stats["ALT-01"]["average"] == 125.0


def test_invalid_parameters(client):
    assert (
        client.get(
            "/missions/1/telemetry?limit=0"
        ).status_code
        == 422
    )

    assert (
        client.get(
            "/missions/1/telemetry?offset=-1"
        ).status_code
        == 422
    )

    # Timestamp without timezone is rejected.
    assert (
        client.get(
            "/missions/1/telemetry"
            "?start=2026-11-01T12:00:00"
        ).status_code
        == 422
    )

    # Start time cannot be later than end time.
    assert (
        client.get(
            "/missions/1/telemetry"
            "?start=2026-11-02T00:00:00Z"
            "&end=2026-11-01T00:00:00Z"
        ).status_code
        == 422
    )
