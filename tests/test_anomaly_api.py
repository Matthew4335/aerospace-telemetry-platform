
import pytest

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

import api.main as api_module


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE sensors (
                sensor_id INTEGER PRIMARY KEY,
                sensor_name TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
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

        conn.execute(text("""
            CREATE TABLE telemetry_anomalies (
                anomaly_id INTEGER PRIMARY KEY,
                reading_id INTEGER NOT NULL UNIQUE,
                anomaly_score REAL NOT NULL,
                model_version TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            INSERT INTO sensors
                (sensor_id, sensor_name, sensor_type,
                 measurement_unit)
            VALUES
                (1, 'ALT-01', 'altitude', 'm'),
                (2, 'VEL-01', 'velocity', 'm/s')
        """))

        conn.execute(text("""
            INSERT INTO telemetry_readings
                (reading_id, mission_id, sensor_id,
                 recorded_at, measurement_value)
            VALUES
                (101, 1, 1, '2026-01-01T12:00:00+00:00', 100),
                (102, 1, 1, '2026-01-01T12:00:01+00:00', 900),
                (103, 1, 2, '2026-01-01T12:00:02+00:00', 45)
        """))

        conn.execute(text("""
            INSERT INTO telemetry_anomalies
                (anomaly_id, reading_id,
                 anomaly_score, model_version)
            VALUES
                (1, 102, -0.15, 'isolation_forest_v1'),
                (2, 103, -0.08, 'isolation_forest_v1')
        """))

    def override_get_db():
        with engine.connect() as conn:
            yield conn

    # The existing Day 9 tests already cover mission lookup.
    # Isolate our new routes from that helper here.
    def fake_find_mission(conn, mission_id):
        if mission_id != 1:
            raise HTTPException(
                status_code=404,
                detail="Mission not found",
            )
        return {"mission_id": 1}

    monkeypatch.setattr(
        api_module,
        "find_mission",
        fake_find_mission,
    )

    api_module.app.dependency_overrides[
        api_module.get_db
    ] = override_get_db

    try:
        with TestClient(api_module.app) as test_client:
            yield test_client
    finally:
        api_module.app.dependency_overrides.pop(
            api_module.get_db,
            None,
        )
        engine.dispose()


def test_list_sensors(client):
    response = client.get("/missions/1/sensors")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert {s["sensor_name"] for s in data} == {
        "ALT-01",
        "VEL-01",
    }


def test_get_all_anomalies(client):
    response = client.get("/missions/1/anomalies")

    assert response.status_code == 200

    data = response.json()

    assert data["mission_id"] == 1
    assert data["total"] == 2
    assert len(data["anomalies"]) == 2


def test_filter_anomalies_by_sensor(client):
    response = client.get(
        "/missions/1/anomalies?sensor_id=1"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["anomalies"][0]["sensor_name"] == "ALT-01"
    assert data["anomalies"][0]["reading_id"] == 102


def test_anomaly_pagination(client):
    response = client.get(
        "/missions/1/anomalies?limit=1&offset=1"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert len(data["anomalies"]) == 1
    assert data["offset"] == 1


def test_nonexistent_mission(client):
    response = client.get("/missions/999/anomalies")

    assert response.status_code == 404


def test_invalid_pagination(client):
    response = client.get(
        "/missions/1/anomalies?limit=-5"
    )

    assert response.status_code == 422


def test_invalid_sensor_id(client):
    response = client.get(
        "/missions/1/anomalies?sensor_id=-1"
    )

    assert response.status_code == 422
