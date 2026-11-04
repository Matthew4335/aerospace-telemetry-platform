
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"


def load_readings():
    return pd.read_csv(RAW_DIR / "telemetry_readings.csv")


def test_expected_row_count():
    df = load_readings()

    assert len(df) == 14995


def test_source_row_ids_are_unique():
    df = load_readings()

    assert df["source_row_id"].is_unique


def test_expected_sensors():
    df = load_readings()

    expected = {
        "ALT-01",
        "VEL-01",
        "TEMP-01",
        "PRESS-01",
        "BATT-01",
    }

    assert set(df["sensor_name"]) == expected


def test_missing_measurements():
    df = load_readings()

    assert df["measurement_value"].isna().sum() == 25


def test_invalid_timestamps():
    df = load_readings()

    parsed = pd.to_datetime(
        df["recorded_at"],
        errors="coerce",
        utc=True,
        format="ISO8601",
    )

    assert parsed.isna().sum() == 10


def test_duplicate_readings():
    df = load_readings()

    key = [
        "mission_name",
        "sensor_name",
        "recorded_at",
        "measurement_value",
    ]

    assert df.duplicated(subset=key).sum() == 30


def test_ground_truth_counts():
    labels = pd.read_csv(
        TRUTH_DIR / "injected_issues.csv"
    )

    expected = {
        "spike": 40,
        "null_value": 25,
        "invalid_timestamp": 10,
        "duplicate": 30,
    }

    assert labels["issue_type"].value_counts().to_dict() == expected


def test_missing_rows_are_tracked():
    missing = pd.read_csv(
        TRUTH_DIR / "missing_readings.csv"
    )

    assert len(missing) == 35


def test_ground_truth_not_leaked_into_raw_data():
    df = load_readings()

    assert "issue_type" not in df.columns
