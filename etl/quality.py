
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# The synthetic generator produces telemetry at 10 Hz.
# That means one sample every 0.1 seconds.
EXPECTED_INTERVAL_SECONDS = 0.1
GAP_THRESHOLD_SECONDS = 0.15

# Illustrative screening ranges for our synthetic sensors.
# These are configurable warnings, NOT certified flight limits.
SENSOR_RANGES = {
    "ALT-01": (-100.0, 100_000.0),    # meters
    "VEL-01": (-2_000.0, 2_000.0),   # m/s
    "TEMP-01": (-273.15, 1_000.0),   # Celsius
    "PRESS-01": (0.0, 500_000.0),    # Pascals
    "BATT-01": (0.0, 30.0),         # volts
}


def validate_metadata(vehicles, missions, sensors):
    """Check source metadata before loading it."""

    tables = [
        (
            "vehicles",
            vehicles,
            ["vehicle_name", "vehicle_type"],
        ),
        (
            "missions",
            missions,
            [
                "vehicle_name",
                "mission_name",
                "launch_time",
                "status",
            ],
        ),
        (
            "sensors",
            sensors,
            [
                "vehicle_name",
                "sensor_name",
                "sensor_type",
                "measurement_unit",
            ],
        ),
    ]

    # Check required columns and missing values.
    for name, df, required in tables:
        missing = set(required) - set(df.columns)

        if missing:
            raise ValueError(
                f"{name}: missing columns {sorted(missing)}"
            )

        if df.empty:
            raise ValueError(f"{name}: source CSV is empty")

        for column in required:
            if (
                df[column].isna().any()
                or df[column].astype(str).str.strip().eq("").any()
            ):
                raise ValueError(
                    f"{name}: missing {column}"
                )

    # Check uniqueness rules from our database.
    if vehicles.duplicated("vehicle_name").any():
        raise ValueError("Duplicate vehicle_name")

    if missions.duplicated("mission_name").any():
        raise ValueError("Duplicate mission_name")

    if sensors.duplicated(
        ["vehicle_name", "sensor_name"]
    ).any():
        raise ValueError(
            "Duplicate vehicle/sensor combination"
        )

    # Every mission and sensor must reference a known vehicle.
    known_vehicles = set(vehicles["vehicle_name"])

    for name, df in [
        ("missions", missions),
        ("sensors", sensors),
    ]:
        unknown = (
            set(df["vehicle_name"]) - known_vehicles
        )

        if unknown:
            raise ValueError(
                f"{name}: unknown vehicles {sorted(unknown)}"
            )

    # Check mission timestamps.
    launch = pd.to_datetime(
        missions["launch_time"],
        utc=True,
        errors="coerce",
        format="ISO8601",
    )

    if launch.isna().any():
        raise ValueError("Invalid mission launch_time")

    if "landing_time" in missions:
        landing = pd.to_datetime(
            missions["landing_time"],
            utc=True,
            errors="coerce",
            format="ISO8601",
        )

        invalid_landing = (
            missions["landing_time"].notna()
            & landing.isna()
        )

        if (
            invalid_landing.any()
            or (landing.notna() & (landing < launch)).any()
        ):
            raise ValueError("Invalid mission landing_time")

    allowed_statuses = [
        "planned",
        "active",
        "completed",
        "aborted",
    ]

    if not missions["status"].isin(allowed_statuses).all():
        raise ValueError("Invalid mission status")


def build_quality_reports(
    valid_rows,
    missions_df,
    mission_lookup,
    sensor_lookup,
):
    """
    Examine valid telemetry without deleting or modifying it.

    Return:
        summary: one row per mission and sensor
        issues: individual quality warnings
    """

    summary_columns = [
        "mission_name",
        "sensor_name",
        "valid_readings",
        "time_gaps",
        "estimated_missing_samples",
        "range_warnings",
        "mission_time_warnings",
    ]

    issue_columns = [
        "mission_name",
        "sensor_name",
        "issue_type",
        "recorded_at",
        "measurement_value",
        "details",
    ]

    summaries = []
    issues = []

    if not valid_rows:
        return (
            pd.DataFrame(columns=summary_columns),
            pd.DataFrame(columns=issue_columns),
        )

    # Translate database IDs back into readable names.
    mission_names = {
        info["mission_id"]: name
        for name, info in mission_lookup.items()
    }

    sensor_names = {
        sensor_id: name
        for (_, name), sensor_id in sensor_lookup.items()
    }

    # Get launch and landing boundaries from the source CSV.
    windows = {}

    for row in missions_df.to_dict("records"):
        launch = pd.to_datetime(
            row["launch_time"], utc=True
        )

        landing_value = row.get("landing_time")

        landing = (
            pd.to_datetime(landing_value, utc=True)
            if pd.notna(landing_value)
            else None
        )

        windows[row["mission_name"]] = (
            launch,
            landing,
        )

    df = pd.DataFrame(valid_rows)

    df["recorded_at"] = pd.to_datetime(
        df["recorded_at"], utc=True
    )

    # Analyze each mission/sensor time series separately.
    df = df.sort_values(
        ["mission_id", "sensor_id", "recorded_at"]
    )

    groups = df.groupby(
        ["mission_id", "sensor_id"]
    )

    for (mission_id, sensor_id), group in groups:

        mission_name = mission_names[mission_id]
        sensor_name = sensor_names[sensor_id]

        launch, landing = windows[mission_name]
        bounds = SENSOR_RANGES.get(sensor_name)

        deltas = (
            group["recorded_at"]
            .diff()
            .dt.total_seconds()
        )

        gaps = 0
        estimated_missing = 0
        range_warnings = 0
        time_warnings = 0

        for index, (_, reading) in enumerate(
            group.iterrows()
        ):
            timestamp = reading["recorded_at"]
            value = float(reading["measurement_value"])
            delta = deltas.iloc[index]

            # Check 1: Missing samples between readings.
            if (
                pd.notna(delta)
                and delta > GAP_THRESHOLD_SECONDS
            ):
                gaps += 1

                missing = max(
                    round(
                        delta / EXPECTED_INTERVAL_SECONDS
                    ) - 1,
                    0,
                )

                estimated_missing += missing

                issues.append({
                    "mission_name": mission_name,
                    "sensor_name": sensor_name,
                    "issue_type": "time_gap",
                    "recorded_at": timestamp.isoformat(),
                    "measurement_value": value,
                    "details": (
                        f"{delta:.3f}s gap; "
                        f"estimated {missing} missing samples"
                    ),
                })

            # Check 2: Values outside screening ranges.
            if (
                bounds is not None
                and not bounds[0] <= value <= bounds[1]
            ):
                range_warnings += 1

                issues.append({
                    "mission_name": mission_name,
                    "sensor_name": sensor_name,
                    "issue_type": "out_of_range",
                    "recorded_at": timestamp.isoformat(),
                    "measurement_value": value,
                    "details": (
                        f"Screening range: "
                        f"[{bounds[0]}, {bounds[1]}]"
                    ),
                })

            # Check 3: Measurements outside mission time.
            if (
                timestamp < launch
                or (
                    landing is not None
                    and timestamp > landing
                )
            ):
                time_warnings += 1

                issues.append({
                    "mission_name": mission_name,
                    "sensor_name": sensor_name,
                    "issue_type": "outside_mission_window",
                    "recorded_at": timestamp.isoformat(),
                    "measurement_value": value,
                    "details": (
                        "Outside mission launch/landing window"
                    ),
                })

        summaries.append({
            "mission_name": mission_name,
            "sensor_name": sensor_name,
            "valid_readings": len(group),
            "time_gaps": gaps,
            "estimated_missing_samples": estimated_missing,
            "range_warnings": range_warnings,
            "mission_time_warnings": time_warnings,
        })

    return (
        pd.DataFrame(summaries, columns=summary_columns),
        pd.DataFrame(issues, columns=issue_columns),
    )


def save_quality_reports(
    directory,
    summary,
    issues,
    source_count,
    valid_count,
    rejected_rows,
    inserted_count,
):
    """Save the current run's quality and ingestion reports."""

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    summary.to_csv(
        directory / "quality_summary.csv",
        index=False,
    )

    issues.to_csv(
        directory / "quality_issues.csv",
        index=False,
    )

    report = {
        "generated_at_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "source_rows": int(source_count),
        "valid_source_rows": int(valid_count),
        "rejected_source_rows": len(rejected_rows),
        "new_database_rows": int(inserted_count),
        "quality_warnings": len(issues),
        "rejection_reasons": dict(
            Counter(
                row["rejection_reason"]
                for row in rejected_rows
            )
        ),
    }

    output = directory / "ingestion_summary.json"

    output.write_text(
        json.dumps(report, indent=2) + "\n"
    )

    return report
