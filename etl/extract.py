
from pathlib import Path

import pandas as pd


# Find the project root regardless of the terminal's directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def read_source_files():
    """Read the source CSV files."""

    vehicles = pd.read_csv(RAW_DIR / "vehicles.csv")
    missions = pd.read_csv(RAW_DIR / "missions.csv")
    sensors = pd.read_csv(RAW_DIR / "sensors.csv")

    readings = pd.read_csv(
        RAW_DIR / "telemetry_readings.csv",
        dtype={
            "mission_name": "string",
            "sensor_name": "string",
            "recorded_at": "string",
        },
    )

    return vehicles, missions, sensors, readings
