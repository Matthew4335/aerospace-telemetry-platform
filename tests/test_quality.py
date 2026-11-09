
import pandas as pd
import pytest

from etl.quality import (
    validate_metadata,
    build_quality_reports,
    save_quality_reports,
)


def sample_metadata():
    vehicles = pd.DataFrame([{
        "vehicle_name": "GTXR Test Vehicle 01",
        "vehicle_type": "rocket",
    }])

    missions = pd.DataFrame([{
        "mission_name": "Test Flight 001",
        "vehicle_name": "GTXR Test Vehicle 01",
        "launch_time": "2026-11-01T12:00:00Z",
        "landing_time": "2026-11-01T12:05:00Z",
        "status": "completed",
    }])

    sensors = pd.DataFrame([{
        "vehicle_name": "GTXR Test Vehicle 01",
        "sensor_name": "ALT-01",
        "sensor_type": "altitude",
        "measurement_unit": "m",
    }])

    return vehicles, missions, sensors


def sample_lookups():
    missions = {
        "Test Flight 001": {
            "mission_id": 1,
            "vehicle_id": 1,
        }
    }

    sensors = {
        (1, "ALT-01"): 10
    }

    return missions, sensors


def sample_readings():
    timestamps = [
        "2026-11-01T12:00:00Z",
        "2026-11-01T12:00:00.100Z",
        "2026-11-01T12:00:00.400Z",
    ]

    values = [100.0, 150.0, 150000.0]

    return [
        {
            "mission_id": 1,
            "sensor_id": 10,
            "recorded_at": pd.Timestamp(time).to_pydatetime(),
            "measurement_value": value,
        }
        for time, value in zip(timestamps, values)
    ]


def test_valid_metadata():
    vehicles, missions, sensors = sample_metadata()

    validate_metadata(vehicles, missions, sensors)


def test_unknown_vehicle_rejected():
    vehicles, missions, sensors = sample_metadata()

    missions["vehicle_name"] = "Unknown Vehicle"

    with pytest.raises(ValueError):
        validate_metadata(vehicles, missions, sensors)


def test_detects_gaps_and_range_warnings():
    _, missions_df, _ = sample_metadata()
    mission_lookup, sensor_lookup = sample_lookups()

    summary, issues = build_quality_reports(
        sample_readings(),
        missions_df,
        mission_lookup,
        sensor_lookup,
    )

    assert summary.iloc[0]["time_gaps"] == 1
    assert summary.iloc[0]["estimated_missing_samples"] == 2
    assert summary.iloc[0]["range_warnings"] == 1

    assert set(issues["issue_type"]) == {
        "time_gap",
        "out_of_range",
    }


def test_detects_outside_mission_window():
    _, missions_df, _ = sample_metadata()
    mission_lookup, sensor_lookup = sample_lookups()

    missions_df["landing_time"] = (
        "2026-11-01T12:00:00.200Z"
    )

    summary, issues = build_quality_reports(
        sample_readings(),
        missions_df,
        mission_lookup,
        sensor_lookup,
    )

    assert summary.iloc[0]["mission_time_warnings"] == 1
    assert "outside_mission_window" in set(
        issues["issue_type"]
    )


def test_saves_quality_reports(tmp_path):
    _, missions_df, _ = sample_metadata()
    mission_lookup, sensor_lookup = sample_lookups()

    summary, issues = build_quality_reports(
        sample_readings(),
        missions_df,
        mission_lookup,
        sensor_lookup,
    )

    report = save_quality_reports(
        tmp_path,
        summary,
        issues,
        source_count=4,
        valid_count=3,
        rejected_rows=[
            {"rejection_reason": "invalid_timestamp"}
        ],
        inserted_count=3,
    )

    assert report["source_rows"] == 4
    assert report["rejected_source_rows"] == 1

    assert (tmp_path / "quality_summary.csv").exists()
    assert (tmp_path / "quality_issues.csv").exists()
    assert (tmp_path / "ingestion_summary.json").exists()
