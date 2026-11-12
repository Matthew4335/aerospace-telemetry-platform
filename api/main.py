
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from fastapi.middleware.cors import CORSMiddleware


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

engine = (
    create_engine(DATABASE_URL, pool_pre_ping=True)
    if DATABASE_URL
    else None
)

app = FastAPI(
    title="Aerospace Telemetry API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)



def get_db():
    """Open one database connection per request."""

    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured",
        )

    with engine.connect() as conn:
        yield conn


# --------------------------------------------------
# RESPONSE MODELS
# --------------------------------------------------

class Mission(BaseModel):
    mission_id: int
    mission_name: str
    vehicle_id: int
    vehicle_name: str
    launch_time: datetime
    landing_time: datetime | None
    status: str


class TelemetryReading(BaseModel):
    reading_id: int
    mission_id: int
    sensor_id: int
    sensor_name: str
    measurement_unit: str
    recorded_at: datetime
    measurement_value: float


class TelemetryPage(BaseModel):
    mission_id: int
    total: int
    limit: int
    offset: int
    readings: list[TelemetryReading]


class SensorStats(BaseModel):
    sensor_id: int
    sensor_name: str
    measurement_unit: str
    reading_count: int
    minimum: float
    maximum: float
    average: float


class MissionStats(BaseModel):
    mission_id: int
    mission_name: str
    total_readings: int
    first_reading: datetime | None
    last_reading: datetime | None
    sensors: list[SensorStats]


class SensorInfo(BaseModel):
    sensor_id: int
    sensor_name: str
    sensor_type: str
    measurement_unit: str


class AnomalyReading(BaseModel):
    anomaly_id: int
    reading_id: int
    mission_id: int
    sensor_id: int
    sensor_name: str
    measurement_unit: str
    recorded_at: datetime
    measurement_value: float
    anomaly_score: float
    model_version: str


class AnomalyPage(BaseModel):
    mission_id: int
    total: int
    limit: int
    offset: int
    anomalies: list[AnomalyReading]



# --------------------------------------------------
# REUSABLE MISSION QUERY
# --------------------------------------------------

MISSION_SQL = """
    SELECT
        m.mission_id,
        m.mission_name,
        m.vehicle_id,
        v.vehicle_name,
        m.launch_time,
        m.landing_time,
        m.status
    FROM missions m
    JOIN vehicles v ON v.vehicle_id = m.vehicle_id
"""


def find_mission(conn: Connection, mission_id: int) -> dict:
    """Return a mission or raise HTTP 404."""

    row = conn.execute(
        text(
            MISSION_SQL
            + " WHERE m.mission_id = :mission_id"
        ),
        {"mission_id": mission_id},
    ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Mission not found",
        )

    return dict(row)


# --------------------------------------------------
# ENDPOINT 1: HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    """Check whether the API process is running."""

    return {"status": "ok"}


# --------------------------------------------------
# ENDPOINT 2: LIST MISSIONS
# --------------------------------------------------

@app.get("/missions", response_model=list[Mission])
def list_missions(
    conn: Connection = Depends(get_db),
):
    """Return all missions."""

    rows = conn.execute(
        text(
            MISSION_SQL
            + " ORDER BY m.mission_id"
        )
    ).mappings().all()

    return [dict(row) for row in rows]


# --------------------------------------------------
# ENDPOINT 3: GET ONE MISSION
# --------------------------------------------------

@app.get("/missions/{mission_id}", response_model=Mission)
def get_mission(
    mission_id: int,
    conn: Connection = Depends(get_db),
):
    """Return one mission by ID."""

    return find_mission(conn, mission_id)


# --------------------------------------------------
# ENDPOINT 4: GET TELEMETRY
# --------------------------------------------------

@app.get(
    "/missions/{mission_id}/telemetry",
    response_model=TelemetryPage,
)
def get_telemetry(
    mission_id: int,
    sensor_id: int | None = Query(default=None, ge=1),
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_db),
):
    """
    Return telemetry with optional filters.

    Supported filters:
        sensor_id
        start
        end

    Pagination:
        limit
        offset
    """

    # Verify the requested mission exists.
    find_mission(conn, mission_id)

    # Require explicit timezones for timestamp filters.
    if start is not None and start.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="start must include a timezone",
        )

    if end is not None and end.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="end must include a timezone",
        )

    if (
        start is not None
        and end is not None
        and start > end
    ):
        raise HTTPException(
            status_code=422,
            detail="start must be before or equal to end",
        )

    # Build filters using SQL parameters.
    conditions = ["t.mission_id = :mission_id"]

    params = {
        "mission_id": mission_id,
        "limit": limit,
        "offset": offset,
    }

    if sensor_id is not None:
        conditions.append(
            "t.sensor_id = :sensor_id"
        )
        params["sensor_id"] = sensor_id

    if start is not None:
        conditions.append(
            "t.recorded_at >= :start"
        )
        params["start"] = start

    if end is not None:
        conditions.append(
            "t.recorded_at <= :end"
        )
        params["end"] = end

    where_sql = " AND ".join(conditions)

    # Count all rows matching the filters.
    total = conn.execute(
        text(f"""
            SELECT COUNT(*)
            FROM telemetry_readings t
            WHERE {where_sql}
        """),
        params,
    ).scalar_one()

    # Retrieve only the requested page.
    rows = conn.execute(
        text(f"""
            SELECT
                t.reading_id,
                t.mission_id,
                t.sensor_id,
                s.sensor_name,
                s.measurement_unit,
                t.recorded_at,
                t.measurement_value
            FROM telemetry_readings t
            JOIN sensors s
                ON s.sensor_id = t.sensor_id
            WHERE {where_sql}
            ORDER BY
                t.recorded_at ASC,
                t.reading_id ASC
            LIMIT :limit
            OFFSET :offset
        """),
        params,
    ).mappings().all()

    return {
        "mission_id": mission_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "readings": [
            dict(row) for row in rows
        ],
    }


# --------------------------------------------------
# ENDPOINT 5: MISSION STATISTICS
# --------------------------------------------------

@app.get(
    "/missions/{mission_id}/stats",
    response_model=MissionStats,
)
def get_mission_stats(
    mission_id: int,
    conn: Connection = Depends(get_db),
):
    """Return mission-wide and per-sensor statistics."""

    mission = find_mission(conn, mission_id)

    # Overall mission statistics.
    totals = conn.execute(
        text("""
            SELECT
                COUNT(*) AS total_readings,
                MIN(recorded_at) AS first_reading,
                MAX(recorded_at) AS last_reading
            FROM telemetry_readings
            WHERE mission_id = :mission_id
        """),
        {"mission_id": mission_id},
    ).mappings().one()

    # Sensor-specific statistics.
    sensor_rows = conn.execute(
        text("""
            SELECT
                s.sensor_id,
                s.sensor_name,
                s.measurement_unit,
                COUNT(*) AS reading_count,
                MIN(t.measurement_value) AS minimum,
                MAX(t.measurement_value) AS maximum,
                AVG(t.measurement_value) AS average
            FROM telemetry_readings t
            JOIN sensors s
                ON s.sensor_id = t.sensor_id
            WHERE t.mission_id = :mission_id
            GROUP BY
                s.sensor_id,
                s.sensor_name,
                s.measurement_unit
            ORDER BY s.sensor_name
        """),
        {"mission_id": mission_id},
    ).mappings().all()

    return {
        "mission_id": mission_id,
        "mission_name": mission["mission_name"],
        "total_readings": totals["total_readings"],
        "first_reading": totals["first_reading"],
        "last_reading": totals["last_reading"],
        "sensors": [
            dict(row) for row in sensor_rows
        ],
    }


@app.get(
    "/missions/{mission_id}/sensors",
    response_model=list[SensorInfo],
)
def list_mission_sensors(
    mission_id: int,
    conn: Connection = Depends(get_db),
):
    # Return 404 if the mission doesn't exist.
    find_mission(conn, mission_id)

    query = text("""
        SELECT DISTINCT
            s.sensor_id,
            s.sensor_name,
            s.sensor_type,
            s.measurement_unit
        FROM sensors AS s
        JOIN telemetry_readings AS r
            ON s.sensor_id = r.sensor_id
        WHERE r.mission_id = :mission_id
        ORDER BY s.sensor_name
    """)

    rows = conn.execute(
        query,
        {"mission_id": mission_id},
    ).mappings().all()

    return [dict(row) for row in rows]


@app.get(
    "/missions/{mission_id}/anomalies",
    response_model=AnomalyPage,
)
def get_mission_anomalies(
    mission_id: int,
    sensor_id: int | None = Query(
        default=None,
        gt=0,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    conn: Connection = Depends(get_db),
):
    # Confirm the mission exists.
    find_mission(conn, mission_id)

    filters = [
        "r.mission_id = :mission_id"
    ]

    params = {
        "mission_id": mission_id,
    }

    if sensor_id is not None:
        filters.append(
            "r.sensor_id = :sensor_id"
        )
        params["sensor_id"] = sensor_id

    where_clause = " AND ".join(filters)

    # Count matching anomalies before pagination.
    count_query = text(f"""
        SELECT COUNT(*)
        FROM telemetry_anomalies AS a
        JOIN telemetry_readings AS r
            ON a.reading_id = r.reading_id
        WHERE {where_clause}
    """)

    total = conn.execute(
        count_query,
        params,
    ).scalar_one()

    # Retrieve the requested anomaly page.
    anomaly_query = text(f"""
        SELECT
            a.anomaly_id,
            a.reading_id,
            r.mission_id,
            r.sensor_id,
            s.sensor_name,
            s.measurement_unit,
            r.recorded_at,
            r.measurement_value,
            a.anomaly_score,
            a.model_version
        FROM telemetry_anomalies AS a
        JOIN telemetry_readings AS r
            ON a.reading_id = r.reading_id
        JOIN sensors AS s
            ON r.sensor_id = s.sensor_id
        WHERE {where_clause}
        ORDER BY
            r.recorded_at,
            a.anomaly_id
        LIMIT :limit
        OFFSET :offset
    """)

    query_params = {
        **params,
        "limit": limit,
        "offset": offset,
    }

    rows = conn.execute(
        anomaly_query,
        query_params,
    ).mappings().all()

    return {
        "mission_id": mission_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "anomalies": [
            dict(row) for row in rows
        ],
    }


